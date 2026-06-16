"""Tests for learning.dataset_export — derive_quality_label and JSONL export (Phase 8)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mechabellum_replay_parser.db.models import Base, Feedback, OutcomeSnapshot, Recommendation
from mechabellum_replay_parser.learning.dataset_export import (
    DatasetRow,
    derive_quality_label,
    export_dataset,
)

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


async def _seed(
    db_factory,
    rec_id: str,
    rating: int | None = None,
    label: str | None = None,
    hp_delta: int | None = None,
    fight_outcome: str | None = None,
):
    async with db_factory() as session:
        async with session.begin():
            rec = Recommendation(
                id=rec_id,
                round_number=3,
                player_name="P",
                status="completed",
                final_recommendation={"summary": "Buy arclight"},
            )
            session.add(rec)
            if rating is not None or label is not None:
                fb = Feedback(
                    recommendation_id=rec_id,
                    rating=rating,
                    label=label,
                )
                session.add(fb)
            if hp_delta is not None or fight_outcome is not None:
                snap = OutcomeSnapshot(
                    recommendation_id=rec_id,
                    next_round_number=4,
                    hp_delta=hp_delta,
                    fight_outcome_next_round=fight_outcome,
                )
                session.add(snap)


# ── derive_quality_label ──────────────────────────────────────────────────────


def test_derive_label_good_high_rating_no_hp_loss():
    assert derive_quality_label(rating=5, label=None, hp_delta=0) == "good"


def test_derive_label_good_high_rating_positive_delta():
    assert derive_quality_label(rating=4, label=None, hp_delta=10) == "good"


def test_derive_label_bad_low_rating():
    assert derive_quality_label(rating=2, label=None, hp_delta=None) == "bad"
    assert derive_quality_label(rating=1, label=None, hp_delta=50) == "bad"


def test_derive_label_illegal_overrides_rating():
    assert derive_quality_label(rating=5, label="bad_illegal", hp_delta=None) == "illegal"


def test_derive_label_positioning_issue():
    assert derive_quality_label(rating=3, label="bad_positioning", hp_delta=None) == "positioning_issue"


def test_derive_label_counter_issue():
    assert derive_quality_label(rating=None, label="bad_counter", hp_delta=None) == "counter_issue"


def test_derive_label_economy_issue():
    assert derive_quality_label(rating=None, label="too_expensive", hp_delta=None) == "economy_issue"


def test_derive_label_unknown_no_info():
    assert derive_quality_label(rating=None, label=None, hp_delta=None) == "unknown"


def test_derive_label_unknown_middle_rating():
    assert derive_quality_label(rating=3, label=None, hp_delta=None) == "unknown"


def test_derive_label_good_requires_nonnegative_delta():
    # rating=4 but hp dropped — not "good"
    assert derive_quality_label(rating=4, label=None, hp_delta=-50) == "unknown"


# ── DatasetRow model ──────────────────────────────────────────────────────────


def test_dataset_row_model():
    row = DatasetRow(
        recommendation_id="r1",
        state_view={"round": 3},
        features={},
        tactical_bundles=[],
        candidate_plans=[],
        selected_plan=None,
        score_breakdowns=[],
        user_feedback={"rating": 5, "label": "good"},
        outcome={"hp_delta": 0},
        derived_quality_label="good",
    )
    assert row.recommendation_id == "r1"
    assert row.derived_quality_label == "good"


def test_dataset_row_serializes_to_json():
    row = DatasetRow(
        recommendation_id="r1",
        state_view={},
        features={},
        tactical_bundles=[],
        candidate_plans=[],
        selected_plan=None,
        score_breakdowns=[],
        user_feedback=None,
        outcome=None,
        derived_quality_label="unknown",
    )
    data = json.loads(row.model_dump_json())
    assert data["recommendation_id"] == "r1"
    assert data["user_feedback"] is None


# ── export_dataset ────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_export_empty_db(db_factory, tmp_path):
    out = tmp_path / "out.jsonl"
    count = await export_dataset(db_factory, out)
    assert count == 0
    assert out.exists()
    assert out.read_text(encoding="utf-8") == ""


@pytest.mark.anyio
async def test_export_single_good_row(db_factory, tmp_path):
    await _seed(db_factory, "rec_good", rating=5, label="good", hp_delta=10)
    out = tmp_path / "out.jsonl"
    count = await export_dataset(db_factory, out)
    assert count == 1

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["recommendation_id"] == "rec_good"
    assert data["derived_quality_label"] == "good"
    assert data["user_feedback"]["rating"] == 5


@pytest.mark.anyio
async def test_export_bad_counter_label(db_factory, tmp_path):
    await _seed(db_factory, "rec_bad", rating=2, label="bad_counter")
    out = tmp_path / "out.jsonl"
    await export_dataset(db_factory, out)

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    data = json.loads(lines[0])
    assert data["derived_quality_label"] == "counter_issue"


@pytest.mark.anyio
async def test_export_no_feedback_unknown_label(db_factory, tmp_path):
    await _seed(db_factory, "rec_nofb")
    out = tmp_path / "out.jsonl"
    await export_dataset(db_factory, out)

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    data = json.loads(lines[0])
    assert data["derived_quality_label"] == "unknown"
    assert data["user_feedback"] is None


@pytest.mark.anyio
async def test_export_with_outcome(db_factory, tmp_path):
    await _seed(db_factory, "rec_with_out", hp_delta=-20, fight_outcome="loss")
    out = tmp_path / "out.jsonl"
    await export_dataset(db_factory, out)

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    data = json.loads(lines[0])
    assert data["outcome"]["hp_delta"] == -20
    assert data["outcome"]["fight_outcome_next_round"] == "loss"


@pytest.mark.anyio
async def test_export_multiple_rows(db_factory, tmp_path):
    await _seed(db_factory, "rec_a", rating=5, hp_delta=5)
    await _seed(db_factory, "rec_b", rating=1)
    await _seed(db_factory, "rec_c")
    out = tmp_path / "out.jsonl"
    count = await export_dataset(db_factory, out)
    assert count == 3

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    labels = {json.loads(line)["derived_quality_label"] for line in lines}
    assert "good" in labels
    assert "bad" in labels
    assert "unknown" in labels


@pytest.mark.anyio
async def test_export_creates_parent_dirs(db_factory, tmp_path):
    out = tmp_path / "nested" / "deep" / "out.jsonl"
    count = await export_dataset(db_factory, out)
    assert count == 0
    assert out.exists()


@pytest.mark.anyio
async def test_export_skips_non_completed(db_factory, tmp_path):
    async with db_factory() as session:
        async with session.begin():
            session.add(Recommendation(
                id="rec_failed", round_number=1, player_name="P", status="failed"
            ))
            session.add(Recommendation(
                id="rec_created", round_number=1, player_name="P", status="created"
            ))
    out = tmp_path / "out.jsonl"
    count = await export_dataset(db_factory, out)
    assert count == 0
