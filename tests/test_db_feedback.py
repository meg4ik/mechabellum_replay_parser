"""DB tests for feedback link and outcome snapshot (Phase 8)."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mechabellum_replay_parser.db.models import Base, Feedback, OutcomeSnapshot, Recommendation
from mechabellum_replay_parser.db.repositories import FeedbackRepository, OutcomeRepository
from mechabellum_replay_parser.db.service import PersistenceService
from mechabellum_replay_parser.learning.outcomes import OutcomeSummary

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def db_factory():
    engine = create_async_engine(_SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def session(db_factory):
    async with db_factory() as s:
        yield s


async def _seed_recommendation(session: AsyncSession, rec_id: str = "rec_1") -> None:
    rec = Recommendation(
        id=rec_id,
        round_number=3,
        player_name="P",
        status="completed",
    )
    session.add(rec)
    await session.flush()


# ── OutcomeSnapshot model ─────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_outcome_snapshot_stores_all_fields(session: AsyncSession):
    await _seed_recommendation(session)
    snap = OutcomeSnapshot(
        recommendation_id="rec_1",
        next_round_number=4,
        before_hp=20,
        next_round_hp=15,
        hp_delta=-5,
        fight_outcome_next_round="loss",
        units_survived_next_round=2,
        enemy_units_survived_next_round=5,
        tower_lost_next_round=True,
        player_followed_plan=False,
        notes="enemy had 5 crawlers",
    )
    session.add(snap)
    await session.commit()

    fetched = await session.get(OutcomeSnapshot, snap.id)
    assert fetched is not None
    assert fetched.before_hp == 20
    assert fetched.next_round_hp == 15
    assert fetched.hp_delta == -5
    assert fetched.fight_outcome_next_round == "loss"
    assert fetched.units_survived_next_round == 2
    assert fetched.enemy_units_survived_next_round == 5
    assert fetched.tower_lost_next_round is True
    assert fetched.player_followed_plan is False
    assert fetched.notes == "enemy had 5 crawlers"


@pytest.mark.anyio
async def test_outcome_snapshot_nullable_fields(session: AsyncSession):
    await _seed_recommendation(session)
    snap = OutcomeSnapshot(
        recommendation_id="rec_1",
        next_round_number=4,
    )
    session.add(snap)
    await session.commit()

    fetched = await session.get(OutcomeSnapshot, snap.id)
    assert fetched is not None
    assert fetched.before_hp is None
    assert fetched.hp_delta is None
    assert fetched.fight_outcome_next_round is None


# ── OutcomeRepository ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_outcome_repo_save(session: AsyncSession):
    await _seed_recommendation(session)
    repo = OutcomeRepository(session)
    snap = await repo.save_outcome_snapshot(
        "rec_1",
        4,
        before_hp=18,
        next_round_hp=12,
        hp_delta=-6,
        fight_outcome_next_round="loss",
        units_survived_next_round=1,
        enemy_units_survived_next_round=3,
        tower_lost_next_round=False,
        player_followed_plan=True,
        notes="held the line",
    )
    await session.commit()
    assert snap.id is not None
    assert snap.hp_delta == -6


@pytest.mark.anyio
async def test_outcome_repo_linked_to_recommendation(session: AsyncSession):
    await _seed_recommendation(session, "rec_link")
    repo = OutcomeRepository(session)
    await repo.save_outcome_snapshot("rec_link", 5, hp_delta=10)
    await session.commit()

    result = await session.execute(
        select(OutcomeSnapshot).where(OutcomeSnapshot.recommendation_id == "rec_link")
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].recommendation_id == "rec_link"


# ── Feedback → Recommendation link ───────────────────────────────────────────


@pytest.mark.anyio
async def test_feedback_links_to_recommendation(session: AsyncSession):
    await _seed_recommendation(session, "rec_fb_link")
    fb_repo = FeedbackRepository(session)
    fb = await fb_repo.save_feedback(
        "rec_fb_link", rating=2, label="bad_counter", followed_plan=False
    )
    assert fb.recommendation_id == "rec_fb_link"


@pytest.mark.anyio
async def test_feedback_and_outcome_both_link(session: AsyncSession):
    await _seed_recommendation(session, "rec_both")

    fb_repo = FeedbackRepository(session)
    outcome_repo = OutcomeRepository(session)

    await fb_repo.save_feedback("rec_both", rating=5, label="good")
    await outcome_repo.save_outcome_snapshot("rec_both", 4, hp_delta=50)
    await session.commit()

    fb_rows = (
        await session.execute(select(Feedback).where(Feedback.recommendation_id == "rec_both"))
    ).scalars().all()
    out_rows = (
        await session.execute(
            select(OutcomeSnapshot).where(OutcomeSnapshot.recommendation_id == "rec_both")
        )
    ).scalars().all()

    assert len(fb_rows) == 1
    assert fb_rows[0].rating == 5
    assert len(out_rows) == 1
    assert out_rows[0].hp_delta == 50


# ── PersistenceService.link_outcome ──────────────────────────────────────────


@pytest.mark.anyio
async def test_link_outcome_disabled_is_noop():
    svc = PersistenceService(None)
    outcome = OutcomeSummary(
        recommendation_id="rec_x", next_round_number=4, hp_delta=-10
    )
    await svc.link_outcome("rec_x", outcome)  # must not raise


@pytest.mark.anyio
async def test_link_outcome_saves_snapshot(db_factory):
    svc = PersistenceService(db_factory)

    async with db_factory() as session:
        rec = Recommendation(id="rec_out", round_number=3, player_name="P", status="completed")
        session.add(rec)
        await session.commit()

    outcome = OutcomeSummary(
        recommendation_id="rec_out",
        next_round_number=4,
        before_hp=20,
        next_round_hp=14,
        hp_delta=-6,
        fight_outcome_next_round="loss",
        tower_lost_next_round=True,
        player_followed_plan=True,
    )
    await svc.link_outcome("rec_out", outcome, next_round_state={"round": 4})

    async with db_factory() as session:
        rows = (
            await session.execute(
                select(OutcomeSnapshot).where(OutcomeSnapshot.recommendation_id == "rec_out")
            )
        ).scalars().all()
    assert len(rows) == 1
    assert rows[0].hp_delta == -6
    assert rows[0].fight_outcome_next_round == "loss"
    assert rows[0].tower_lost_next_round is True
    assert rows[0].next_round_state == {"round": 4}
