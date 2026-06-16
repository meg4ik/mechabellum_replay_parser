"""Integration tests for the LLM pipeline using JSON fixtures and a fake provider.

Covers: planner output parsing, judge output parsing, invalid JSON fallback,
validator blocking a bad plan, and the full pipeline producing placement output.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from mechabellum_replay_parser.coach.engine import CoachAnalysis, CoachEngine
from mechabellum_replay_parser.coach.planner import Planner
from mechabellum_replay_parser.coach.judge import Judge
from mechabellum_replay_parser.coach.schemas import (
    CandidatePlan,
    PlayerRoundView,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    UnitView,
)
from mechabellum_replay_parser.coach.validator import PlanValidator
from mechabellum_replay_parser.coach.legal_actions import LegalActionGenerator
from mechabellum_replay_parser.llm.providers.local_provider import LocalProvider

FIXTURES = Path(__file__).parent / "fixtures"


# ── Fake multi-response provider ──────────────────────────────────────────────


class _SequentialProvider:
    """Returns responses in order; last response repeats for extra calls."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self._idx = 0

    async def complete_json(self, system, user, schema=None, temperature=0.2):
        resp = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        return resp

    def stream_text(self, system, user, temperature=0.2):
        async def _gen():
            yield ""

        return _gen()


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def planner_valid():
    return json.loads((FIXTURES / "llm_planner_valid.json").read_text())


@pytest.fixture
def planner_invalid():
    return json.loads((FIXTURES / "llm_planner_invalid.json").read_text())


@pytest.fixture
def judge_valid():
    return json.loads((FIXTURES / "llm_judge_valid.json").read_text())


@pytest.fixture
def parsed_early():
    return json.loads((FIXTURES / "parsed_round_early.json").read_text())


@pytest.fixture
def parsed_air_threat():
    return json.loads((FIXTURES / "parsed_round_air_threat.json").read_text())


@pytest.fixture
def parsed_construction():
    return json.loads((FIXTURES / "parsed_round_construction.json").read_text())


def _simple_state(supply: int = 300) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=2,
        player_name="Player1",
        enemy_names=["Player2"],
        my_supply=supply,
        my_state=PlayerRoundView(
            name="Player1",
            army_value=200,
            units=[UnitView(name="crawler", index=0)],
            shop=ShopView(
                unlocked=["crawler", "arclight"],
                locked=[],
                buys_remaining=3,
                unlocks_remaining=1,
            ),
        ),
        enemy_states=[PlayerRoundView(name="Player2", army_value=200)],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _no_features() -> TacticalFeatures:
    return TacticalFeatures(
        threats=[],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )


# ── Planner parsing ───────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_planner_parses_valid_fixture(planner_valid):
    planner = Planner(LocalProvider(json_response=planner_valid), system_prompt="test")
    plans = await planner.generate_plans(_simple_state(), _no_features(), [])
    assert len(plans) == 2
    assert plans[0].id == "plan_buy_arclight"
    assert plans[1].id == "plan_buy_mustang"


@pytest.mark.anyio
async def test_planner_falls_back_on_invalid_fixture(planner_invalid):
    planner = Planner(
        LocalProvider(json_response=planner_invalid), system_prompt="test"
    )
    plans = await planner.generate_plans(_simple_state(), _no_features(), [])
    assert len(plans) == 1
    assert plans[0].id == "plan_fallback"


# ── Judge parsing ─────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_judge_parses_valid_fixture(planner_valid, judge_valid):
    state = _simple_state()
    planner = Planner(LocalProvider(json_response=planner_valid), system_prompt="test")
    plans = await planner.generate_plans(state, _no_features(), [])
    validator = PlanValidator()
    gen = LegalActionGenerator()
    legal_actions, _ = gen.generate(state, _no_features())
    validated = [
        (p, validator.validate_placement(p.placement, state, legal_actions))
        for p in plans
    ]

    judge = Judge(LocalProvider(json_response=judge_valid), system_prompt="test")
    output = await judge.select_plan(state, _no_features(), validated)
    assert output.best_plan_id == "plan_buy_arclight"
    assert output.confidence > 0.5


# ── Validator blocks bad plan ─────────────────────────────────────────────────


def test_validator_blocks_locked_unit_buy():
    """Buying a unit not in shop.unlocked is an error that invalidates the plan."""
    state = _simple_state(supply=500)
    plan = CandidatePlan(
        id="plan_locked",
        title="Buy Locked Unit",
        action_ids=[],
        total_cost=100,
        main_goal="Buy a locked unit",
        why_it_works="It does not",
        risks=[],
        expected_enemy_response=[],
        # "fortress" is not in shop.unlocked (["crawler", "arclight"])
        placement=[{"unit": "fortress", "x": 0, "y": -90, "action": "new"}],
        confidence=0.5,
    )
    gen = LegalActionGenerator()
    legal_actions, _ = gen.generate(state, _no_features())
    validator = PlanValidator()
    result = validator.validate_placement(plan.placement, state, legal_actions)
    assert not result.is_valid
    assert any(i.code == "unit_not_unlocked" for i in result.issues)


def test_validator_warns_on_supply_overspend():
    """Supply overspend is a warning (not an error), plan stays valid."""
    state = _simple_state(supply=50)
    plan = CandidatePlan(
        id="plan_overspend",
        title="Overspend",
        action_ids=[],
        total_cost=500,
        main_goal="Overspend",
        why_it_works="costly",
        risks=[],
        expected_enemy_response=[],
        placement=[{"unit": "arclight", "x": 0, "y": -90, "action": "new"}],
        confidence=0.5,
    )
    gen = LegalActionGenerator()
    legal_actions, _ = gen.generate(state, _no_features())
    validator = PlanValidator()
    result = validator.validate_placement(plan.placement, state, legal_actions)
    assert result.is_valid
    assert any(i.severity == "warning" for i in result.issues)


# ── Full pipeline with fixture data ───────────────────────────────────────────


@pytest.mark.anyio
async def test_full_pipeline_early_game(parsed_early, planner_valid, judge_valid):
    engine = CoachEngine(provider=_SequentialProvider([planner_valid, judge_valid]))
    analysis = await engine.analyze_replay_detailed(
        parsed_early, supply=200, player_name="Player1"
    )
    assert isinstance(analysis, CoachAnalysis)
    assert analysis.recommendation is not None
    assert analysis.recommendation.summary


@pytest.mark.anyio
async def test_full_pipeline_air_threat(parsed_air_threat, planner_valid, judge_valid):
    engine = CoachEngine(provider=_SequentialProvider([planner_valid, judge_valid]))
    analysis = await engine.analyze_replay_detailed(
        parsed_air_threat, supply=300, player_name="Player1"
    )
    assert analysis.recommendation is not None
    assert len(analysis.validated_plans) >= 1


@pytest.mark.anyio
async def test_full_pipeline_construction(
    parsed_construction, planner_valid, judge_valid
):
    engine = CoachEngine(provider=_SequentialProvider([planner_valid, judge_valid]))
    analysis = await engine.analyze_replay_detailed(
        parsed_construction, supply=250, player_name="Player1"
    )
    assert analysis.recommendation is not None


@pytest.mark.anyio
async def test_pipeline_emits_placement(parsed_early, planner_valid, judge_valid):
    engine = CoachEngine(provider=_SequentialProvider([planner_valid, judge_valid]))
    analysis = await engine.analyze_replay_detailed(
        parsed_early, supply=200, player_name="Player1"
    )
    # Placement is resolved from placement_intents by code, not from LLM raw coords
    assert analysis.recommendation.placement is not None
    assert len(analysis.recommendation.placement) > 0


@pytest.mark.anyio
async def test_final_recommendation_contains_resolved_placement(
    parsed_early, planner_valid, judge_valid
):
    """Placement in final recommendation comes from PlacementResolver, not LLM."""
    engine = CoachEngine(provider=_SequentialProvider([planner_valid, judge_valid]))
    analysis = await engine.analyze_replay_detailed(
        parsed_early, supply=200, player_name="Player1"
    )
    assert analysis.judge_output is not None
    # Judge output must never contain placement — it only chooses the plan ID
    assert analysis.judge_output.placement == []
    # Resolved placements are the source of truth for coordinates
    assert analysis.recommendation.resolved_placements is not None


@pytest.mark.anyio
async def test_pipeline_invalid_planner_uses_fallback(
    parsed_early, planner_invalid, judge_valid
):
    """When planner returns invalid JSON, fallback plan is used and pipeline still completes."""
    engine = CoachEngine(provider=_SequentialProvider([planner_invalid, judge_valid]))
    analysis = await engine.analyze_replay_detailed(
        parsed_early, supply=200, player_name="Player1"
    )
    assert analysis.recommendation is not None
    assert len(analysis.validated_plans) == 1
    assert analysis.validated_plans[0][0].id == "plan_fallback"


# ── LLM timeout fallback ──────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_planner_timeout_uses_fallback(monkeypatch):
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "0.001")

    class _SlowProvider:
        async def complete_json(self, system, user, schema=None, temperature=0.2):
            await asyncio.sleep(10)
            return {"plans": []}

        def stream_text(self, system, user, temperature=0.2):
            async def _gen():
                yield ""

            return _gen()

    # The timeout fires at engine level; here we test via engine
    engine = CoachEngine(provider=_SlowProvider())
    analysis = await engine.analyze_replay_detailed(
        json.loads((FIXTURES / "parsed_round_early.json").read_text()),
        supply=200,
        player_name="Player1",
    )
    assert analysis.recommendation is not None
    assert analysis.validated_plans[0][0].id == "plan_fallback"


@pytest.mark.anyio
async def test_judge_timeout_uses_fallback(monkeypatch, planner_valid):
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "0.001")

    class _FastPlannerSlowJudge:
        def __init__(self):
            self._calls = 0

        async def complete_json(self, system, user, schema=None, temperature=0.2):
            self._calls += 1
            if self._calls == 1:
                return planner_valid
            await asyncio.sleep(10)
            return {}

        def stream_text(self, system, user, temperature=0.2):
            async def _gen():
                yield ""

            return _gen()

    engine = CoachEngine(provider=_FastPlannerSlowJudge())
    analysis = await engine.analyze_replay_detailed(
        json.loads((FIXTURES / "parsed_round_early.json").read_text()),
        supply=200,
        player_name="Player1",
    )
    assert analysis.recommendation is not None
    assert analysis.judge_output is not None
