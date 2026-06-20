"""Tests for influence-extended dataset export (Phase 09)."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mechabellum_replay_parser.db.models import (
    Base,
    CandidatePlanRow,
    Feedback,
    Recommendation,
)
from mechabellum_replay_parser.learning.dataset_export import (
    DatasetRow,
    export_dataset,
)

_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_factory():
    engine = create_async_engine(_SQLITE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed_with_influence(db_factory, rec_id="r1"):
    async with db_factory() as session:
        async with session.begin():
            rec = Recommendation(
                id=rec_id,
                round_number=3,
                player_name="P",
                status="completed",
                final_recommendation={"summary": "Buy arclight"},
                influence_summary_json={"ground_balance": "enemy_favored"},
                influence_findings_json=[{"key": "anti_air_gap", "severity": 0.8}],
            )
            session.add(rec)
            cp = CandidatePlanRow(
                recommendation_id=rec_id,
                plan_key="p1",
                planner_output={"id": "p1", "title": "Anti-air"},
                validation_result={"is_valid": True, "issues": []},
                is_selected=True,
                plan_score_json={
                    "plan_id": "p1",
                    "total_score": 0.7,
                    "influence_improvement": 0.6,
                },
                influence_delta_json={
                    "influence_improvement": 0.6,
                    "anti_air_improvement": 0.5,
                },
            )
            session.add(cp)
            fb = Feedback(
                recommendation_id=rec_id,
                rating=4,
                label="good",
            )
            session.add(fb)


async def _seed_without_influence(db_factory, rec_id="r2"):
    async with db_factory() as session:
        async with session.begin():
            rec = Recommendation(
                id=rec_id,
                round_number=2,
                player_name="P",
                status="completed",
                final_recommendation={"summary": "Buy crawler"},
            )
            session.add(rec)
            cp = CandidatePlanRow(
                recommendation_id=rec_id,
                plan_key="p2",
                planner_output={"id": "p2", "title": "Default"},
                validation_result={"is_valid": True, "issues": []},
                is_selected=True,
            )
            session.add(cp)


# ── DatasetRow includes influence fields ─────────────────────────────────────


def test_dataset_row_has_influence_fields():
    row = DatasetRow(
        recommendation_id="r1",
        state_view={},
        features={},
        tactical_bundles=[],
        candidate_plans=[],
        selected_plan=None,
        score_breakdowns=[],
        influence_summary={"ground_balance": "neutral"},
        influence_findings=[{"key": "anti_air_gap"}],
        plan_influence_deltas=[{"plan_id": "p1", "influence_improvement": 0.6}],
        derived_quality_label="good",
    )
    assert row.influence_summary is not None
    assert row.influence_findings is not None
    assert row.plan_influence_deltas is not None


def test_dataset_row_backward_compat():
    row = DatasetRow(
        recommendation_id="r1",
        state_view={},
        features={},
        tactical_bundles=[],
        candidate_plans=[],
        selected_plan=None,
        score_breakdowns=[],
        derived_quality_label="unknown",
    )
    assert row.influence_summary is None
    assert row.influence_findings is None
    assert row.plan_influence_deltas is None


# ── Export includes influence from DB ────────────────────────────────────────


@pytest.mark.anyio
async def test_export_includes_influence(db_factory, tmp_path):
    await _seed_with_influence(db_factory)
    out = tmp_path / "export.jsonl"
    count = await export_dataset(db_factory, out)
    assert count == 1

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    data = json.loads(lines[0])
    assert data["influence_summary"] == {"ground_balance": "enemy_favored"}
    assert data["influence_findings"][0]["key"] == "anti_air_gap"
    assert len(data["score_breakdowns"]) == 1
    assert data["score_breakdowns"][0]["influence_improvement"] == 0.6
    assert data["plan_influence_deltas"][0]["anti_air_improvement"] == 0.5


@pytest.mark.anyio
async def test_export_without_influence_still_works(db_factory, tmp_path):
    await _seed_without_influence(db_factory)
    out = tmp_path / "export.jsonl"
    count = await export_dataset(db_factory, out)
    assert count == 1

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    data = json.loads(lines[0])
    assert data["influence_summary"] is None
    assert data["influence_findings"] is None
    assert data["plan_influence_deltas"] is None


@pytest.mark.anyio
async def test_export_mixed_rows(db_factory, tmp_path):
    await _seed_with_influence(db_factory, rec_id="r1")
    await _seed_without_influence(db_factory, rec_id="r2")
    out = tmp_path / "export.jsonl"
    count = await export_dataset(db_factory, out)
    assert count == 2

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    row1 = json.loads(lines[0])
    row2 = json.loads(lines[1])
    assert row1["influence_summary"] is not None
    assert row2["influence_summary"] is None
