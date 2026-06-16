"""Phase 8 tests — DB models, repositories, and PersistenceService.

Uses SQLite in-memory (aiosqlite) so no Postgres required.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mechabellum_replay_parser.coach.schemas import (
    CandidatePlan,
    CoachRecommendation,
    JudgeOutput,
    PlanValidationResult,
)
from mechabellum_replay_parser.db.models import (
    Base,
    CandidatePlanRow,
    Feedback,
    LLMCall,
    Match,
    Recommendation,
    Round,
)
from mechabellum_replay_parser.db.repositories import (
    FeedbackRepository,
    RecommendationRepository,
)
from mechabellum_replay_parser.db.service import PersistenceService
from mechabellum_replay_parser.coach.engine import CoachAnalysis

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


# ── Models: basic instantiation ───────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_match(session: AsyncSession):
    row = Match(
        source_file="replay.grbr",
        match_mode="VS_1_1",
        player_name="Alice",
        teams=[["Alice"], ["Bob"]],
    )
    session.add(row)
    await session.commit()
    assert row.id is not None
    assert row.source_file == "replay.grbr"


@pytest.mark.anyio
async def test_create_round(session: AsyncSession):
    match = Match(source_file="x.grbr", match_mode="VS_1_1", player_name="P1", teams=[])
    session.add(match)
    await session.flush()
    round_ = Round(match_id=match.id, round_number=3, raw_round={"round": 3})
    session.add(round_)
    await session.commit()
    assert round_.id is not None
    assert round_.round_number == 3


@pytest.mark.anyio
async def test_create_recommendation(session: AsyncSession):
    match = Match(source_file="x.grbr", match_mode="VS_1_1", player_name="P1", teams=[])
    session.add(match)
    await session.flush()
    rec = Recommendation(
        id="rec_abc123",
        match_id=match.id,
        round_number=5,
        player_name="P1",
        status="completed",
    )
    session.add(rec)
    await session.commit()
    assert rec.id == "rec_abc123"
    assert rec.status == "completed"


@pytest.mark.anyio
async def test_candidate_plan_row(session: AsyncSession):
    match = Match(source_file="x.grbr", match_mode="VS_1_1", player_name="P1", teams=[])
    session.add(match)
    await session.flush()
    rec = Recommendation(
        id="rec_1",
        match_id=match.id,
        round_number=1,
        player_name="P1",
        status="created",
    )
    session.add(rec)
    await session.flush()
    cp = CandidatePlanRow(
        recommendation_id="rec_1",
        plan_key="plan_alpha",
        planner_output={"id": "plan_alpha"},
        is_selected=True,
    )
    session.add(cp)
    await session.commit()
    assert cp.is_selected is True


@pytest.mark.anyio
async def test_llm_call_row(session: AsyncSession):
    match = Match(source_file="x.grbr", match_mode="VS_1_1", player_name="P1", teams=[])
    session.add(match)
    await session.flush()
    rec = Recommendation(
        id="rec_2",
        match_id=match.id,
        round_number=2,
        player_name="P1",
        status="created",
    )
    session.add(rec)
    await session.flush()
    lc = LLMCall(recommendation_id="rec_2", stage="planner", model="gpt-4o")
    session.add(lc)
    await session.commit()
    assert lc.stage == "planner"
    assert lc.model == "gpt-4o"


@pytest.mark.anyio
async def test_feedback_row(session: AsyncSession):
    match = Match(source_file="x.grbr", match_mode="VS_1_1", player_name="P1", teams=[])
    session.add(match)
    await session.flush()
    rec = Recommendation(
        id="rec_3",
        match_id=match.id,
        round_number=3,
        player_name="P1",
        status="completed",
    )
    session.add(rec)
    await session.flush()
    fb = Feedback(recommendation_id="rec_3", rating=4, label="good", followed_plan=True)
    session.add(fb)
    await session.commit()
    assert fb.rating == 4
    assert fb.label == "good"


# ── Repositories ──────────────────────────────────────────────────────────────


def _make_recommendation() -> CoachRecommendation:
    return CoachRecommendation(
        summary="Buy Arclight",
        confidence=0.8,
        placement=[{"unit": "arclight", "x": 1, "y": 2}],
    )


def _make_validated_plans() -> list[tuple[CandidatePlan, PlanValidationResult]]:
    plan = CandidatePlan(
        id="plan_a",
        title="Plan A",
        action_ids=["buy_arclight"],
        total_cost=100,
        main_goal="Counter crawlers",
        why_it_works="Arclight clears chaff",
        risks=["exposed to marksman"],
        expected_enemy_response=["buy marksman"],
        placement=[{"unit": "arclight", "x": 0, "y": 0}],
        confidence=0.75,
    )
    validation = PlanValidationResult(plan_id="plan_a", is_valid=True, issues=[])
    return [(plan, validation)]


@pytest.mark.anyio
async def test_repo_create_match(session: AsyncSession):
    repo = RecommendationRepository(session)
    row = await repo.create_match(
        "replay.grbr", "VS_1_1", "Alice", [["Alice"], ["Bob"]]
    )
    await session.commit()
    assert row.id is not None
    assert row.match_mode == "VS_1_1"


@pytest.mark.anyio
async def test_repo_create_round(session: AsyncSession):
    repo = RecommendationRepository(session)
    match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
    round_ = await repo.create_round(match.id, 4, raw_round={"round": 4})
    await session.commit()
    assert round_.round_number == 4
    assert round_.match_id == match.id


@pytest.mark.anyio
async def test_repo_create_and_complete_recommendation(session: AsyncSession):
    repo = RecommendationRepository(session)
    match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
    round_ = await repo.create_round(match.id, 1)
    await repo.create_recommendation("rec_x", match.id, round_.id, 1, "P")
    rec = _make_recommendation()
    await repo.mark_completed("rec_x", rec, supply=250)
    await session.commit()

    fetched = await session.get(Recommendation, "rec_x")
    assert fetched is not None
    assert fetched.status == "completed"
    assert fetched.supply == 250
    assert fetched.final_summary == "Buy Arclight"
    assert fetched.confidence == pytest.approx(0.8)


@pytest.mark.anyio
async def test_repo_mark_failed(session: AsyncSession):
    repo = RecommendationRepository(session)
    match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
    round_ = await repo.create_round(match.id, 1)
    await repo.create_recommendation("rec_fail", match.id, round_.id, 1, "P")
    await repo.mark_failed("rec_fail")
    await session.commit()

    fetched = await session.get(Recommendation, "rec_fail")
    assert fetched is not None
    assert fetched.status == "failed"


@pytest.mark.anyio
async def test_repo_save_candidate_plans(session: AsyncSession):
    repo = RecommendationRepository(session)
    match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
    round_ = await repo.create_round(match.id, 1)
    await repo.create_recommendation("rec_cp", match.id, round_.id, 1, "P")
    vplans = _make_validated_plans()
    await repo.save_candidate_plans("rec_cp", vplans, selected_plan_id="plan_a")
    await session.commit()

    fetched = await session.get(Recommendation, "rec_cp")
    assert fetched is not None
    # Can't easily lazy-load in async; just verify no error occurred
    from sqlalchemy import select

    result = await session.execute(
        select(CandidatePlanRow).where(CandidatePlanRow.recommendation_id == "rec_cp")
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].plan_key == "plan_a"
    assert rows[0].is_selected is True


@pytest.mark.anyio
async def test_repo_save_llm_calls(session: AsyncSession):
    repo = RecommendationRepository(session)
    match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
    round_ = await repo.create_round(match.id, 1)
    await repo.create_recommendation("rec_llm", match.id, round_.id, 1, "P")
    await repo.save_llm_calls(
        "rec_llm",
        [
            {"stage": "planner", "model": "gpt-4o"},
            {"stage": "judge", "model": "gpt-4o"},
        ],
    )
    await session.commit()

    from sqlalchemy import select

    result = await session.execute(
        select(LLMCall).where(LLMCall.recommendation_id == "rec_llm")
    )
    rows = result.scalars().all()
    assert len(rows) == 2
    stages = {r.stage for r in rows}
    assert stages == {"planner", "judge"}


@pytest.mark.anyio
async def test_feedback_repo_save(session: AsyncSession):
    # Pre-create recommendation (no match needed for FK in SQLite without enforcement)
    rec = Recommendation(
        id="rec_fb", round_number=1, player_name="P", status="completed"
    )
    session.add(rec)
    await session.flush()

    repo = FeedbackRepository(session)
    fb = await repo.save_feedback(
        "rec_fb", rating=5, label="good", comment="Nice", followed_plan=True
    )
    assert fb.id is not None
    assert fb.rating == 5


# ── PersistenceService ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_persistence_service_disabled():
    svc = PersistenceService(None)
    assert not svc.enabled
    # Should be a no-op — no error raised
    await svc.save_feedback("rec_x", rating=3)
    await svc.save_match_analysis(
        rec_id="rec_x",
        source_file="x.grbr",
        parsed={"metadata": {}, "teams": [], "rounds": []},
        round_number=1,
        player_name="P",
        supply=None,
        analysis=CoachAnalysis(recommendation=_make_recommendation()),
    )


@pytest.mark.anyio
async def test_persistence_service_enabled(db_factory):
    svc = PersistenceService(db_factory)
    assert svc.enabled

    rec = _make_recommendation()
    judge = JudgeOutput(
        best_plan_id="plan_a",
        confidence=0.9,
        main_reason="Best anti-chaff option",
    )
    analysis = CoachAnalysis(
        recommendation=rec,
        validated_plans=_make_validated_plans(),
        judge_output=judge,
        model_name="gpt-4o",
    )
    parsed = {
        "metadata": {"match_mode": "VS_1_1"},
        "teams": [["P1"], ["P2"]],
        "rounds": [{"round": 2, "players": {}}],
    }

    await svc.save_match_analysis(
        rec_id="rec_svc_1",
        source_file="test.grbr",
        parsed=parsed,
        round_number=2,
        player_name="P1",
        supply=300,
        analysis=analysis,
    )

    # Verify rows exist
    async with db_factory() as session:
        fetched = await session.get(Recommendation, "rec_svc_1")
        assert fetched is not None
        assert fetched.status == "completed"
        assert fetched.supply == 300
        assert fetched.model_name == "gpt-4o"

        from sqlalchemy import select

        cp_rows = (
            (
                await session.execute(
                    select(CandidatePlanRow).where(
                        CandidatePlanRow.recommendation_id == "rec_svc_1"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(cp_rows) == 1
        assert cp_rows[0].is_selected is True

        llm_rows = (
            (
                await session.execute(
                    select(LLMCall).where(LLMCall.recommendation_id == "rec_svc_1")
                )
            )
            .scalars()
            .all()
        )
        assert len(llm_rows) == 2


@pytest.mark.anyio
async def test_persistence_service_save_feedback(db_factory):
    svc = PersistenceService(db_factory)

    async with db_factory() as session:
        rec = Recommendation(
            id="rec_fbsvc", round_number=1, player_name="P", status="completed"
        )
        session.add(rec)
        await session.commit()

    await svc.save_feedback("rec_fbsvc", rating=4, label="good", followed_plan=True)

    async with db_factory() as session:
        from sqlalchemy import select

        rows = (
            (
                await session.execute(
                    select(Feedback).where(Feedback.recommendation_id == "rec_fbsvc")
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].rating == 4
        assert rows[0].label == "good"
