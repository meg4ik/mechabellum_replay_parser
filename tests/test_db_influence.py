"""Tests for influence data persistence (Phase 09)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from mechabellum_replay_parser.db.models import (
    Base,
    CandidatePlanRow,
    Recommendation,
)
from mechabellum_replay_parser.db.repositories import RecommendationRepository
from mechabellum_replay_parser.coach.schemas import (
    CandidatePlan,
    CoachRecommendation,
    PlanValidationResult,
    PlanScoreBreakdown,
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


def _plan(plan_id="p1"):
    return CandidatePlan(
        id=plan_id, title="test", action_ids=["buy_arclight"],
        total_cost=100, main_goal="test", why_it_works="test",
        risks=[], expected_enemy_response=[], confidence=0.5,
    )


def _valid(plan_id="p1"):
    return PlanValidationResult(plan_id=plan_id, is_valid=True, issues=[])


def _score(plan_id="p1"):
    return PlanScoreBreakdown(
        plan_id=plan_id, total_score=0.7, threat_coverage=0.8,
        supply_efficiency=0.6, tempo=0.5, scaling=0.3,
        positioning_safety=0.6, tower_protection=0.5,
        flexibility_next_round=0.8, overreaction_risk=0.0,
        legality_penalty=0.0,
        influence_improvement=0.6, anti_air_improvement=0.5,
        anti_chaff_improvement=0.0, anti_heavy_improvement=0.0,
        artillery_risk_reduction=0.0,
        influence_explanation=["Addresses anti-air gap."],
    )


def _recommendation():
    return CoachRecommendation(summary="Buy arclight", coach_text="Do it.")


# ── Influence fields saved to recommendation ────────────────────────────────


@pytest.mark.anyio
async def test_influence_summary_saved(db_factory):
    async with db_factory() as session:
        async with session.begin():
            repo = RecommendationRepository(session)
            match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
            await repo.create_recommendation(
                rec_id="r1", match_id=match.id, round_id=None,
                round_number=3, player_name="P",
            )
            await repo.mark_completed(
                rec_id="r1",
                recommendation=_recommendation(),
                supply=600,
                influence_summary_json={"ground_balance": "enemy_favored"},
                influence_findings_json=[{"key": "anti_air_gap", "severity": 0.8}],
            )

    async with db_factory() as session:
        rec = await session.get(Recommendation, "r1")
        assert rec is not None
        assert rec.influence_summary_json == {"ground_balance": "enemy_favored"}
        assert rec.influence_findings_json[0]["key"] == "anti_air_gap"


@pytest.mark.anyio
async def test_influence_null_when_not_provided(db_factory):
    async with db_factory() as session:
        async with session.begin():
            repo = RecommendationRepository(session)
            match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
            await repo.create_recommendation(
                rec_id="r2", match_id=match.id, round_id=None,
                round_number=3, player_name="P",
            )
            await repo.mark_completed(
                rec_id="r2", recommendation=_recommendation(), supply=600,
            )

    async with db_factory() as session:
        rec = await session.get(Recommendation, "r2")
        assert rec.influence_summary_json is None
        assert rec.influence_findings_json is None


# ── Plan scores and influence deltas saved to candidate_plans ────────────────


@pytest.mark.anyio
async def test_plan_score_saved(db_factory):
    async with db_factory() as session:
        async with session.begin():
            repo = RecommendationRepository(session)
            match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
            await repo.create_recommendation(
                rec_id="r3", match_id=match.id, round_id=None,
                round_number=3, player_name="P",
            )
            await repo.save_candidate_plans(
                rec_id="r3",
                validated_plans=[(_plan(), _valid())],
                selected_plan_id="p1",
                score_breakdowns=[_score()],
            )

    async with db_factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(CandidatePlanRow).where(CandidatePlanRow.recommendation_id == "r3")
        )
        cp = result.scalar_one()
        assert cp.plan_score_json is not None
        assert cp.plan_score_json["total_score"] == 0.7
        assert cp.influence_delta_json is not None
        assert cp.influence_delta_json["influence_improvement"] == 0.6
        assert cp.influence_delta_json["anti_air_improvement"] == 0.5


@pytest.mark.anyio
async def test_plan_score_null_without_breakdowns(db_factory):
    async with db_factory() as session:
        async with session.begin():
            repo = RecommendationRepository(session)
            match = await repo.create_match("f.grbr", "VS_1_1", "P", [])
            await repo.create_recommendation(
                rec_id="r4", match_id=match.id, round_id=None,
                round_number=3, player_name="P",
            )
            await repo.save_candidate_plans(
                rec_id="r4",
                validated_plans=[(_plan(), _valid())],
                selected_plan_id="p1",
            )

    async with db_factory() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(CandidatePlanRow).where(CandidatePlanRow.recommendation_id == "r4")
        )
        cp = result.scalar_one()
        assert cp.plan_score_json is None
        assert cp.influence_delta_json is None
