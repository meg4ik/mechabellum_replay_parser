"""Tests for Judge using LocalProvider (no real LLM)."""

import pytest

from mechabellum_replay_parser.coach.feature_extractor import FeatureExtractor
from mechabellum_replay_parser.coach.judge import Judge, _make_fallback_judge_output
from mechabellum_replay_parser.coach.legal_actions import LegalActionGenerator
from mechabellum_replay_parser.coach.planner import _make_fallback_plan
from mechabellum_replay_parser.coach.schemas import (
    CandidatePlan,
    JudgeOutput,
    PlayerRoundView,
    PlanValidationResult,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ValidationIssue,
)
from mechabellum_replay_parser.coach.state_view import StateViewBuilder
from mechabellum_replay_parser.coach.validator import PlanValidator
from mechabellum_replay_parser.llm.providers.local_provider import LocalProvider


def _make_state() -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=3,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=300,
        my_state=PlayerRoundView(name="Me", army_value=600),
        enemy_states=[PlayerRoundView(name="Enemy", army_value=700)],
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


def _make_plan(plan_id: str = "plan_1", confidence: float = 0.7) -> CandidatePlan:
    return CandidatePlan(
        id=plan_id,
        title="Test plan",
        action_ids=["buy_arclight"],
        total_cost=100,
        main_goal="Counter air",
        why_it_works="Arclight counters air units.",
        risks=[],
        expected_enemy_response=[],
        placement=[{"unit": "arclight", "x": 0, "y": -100, "action": "new"}],
        confidence=confidence,
    )


def _valid_result(plan_id: str = "plan_1") -> PlanValidationResult:
    return PlanValidationResult(plan_id=plan_id, is_valid=True, issues=[])


def _invalid_result(plan_id: str = "plan_1") -> PlanValidationResult:
    return PlanValidationResult(
        plan_id=plan_id,
        is_valid=False,
        issues=[
            ValidationIssue(severity="error", code="too_many_buys", message="too many")
        ],
    )


def _make_judge(json_response: dict) -> Judge:
    return Judge(
        LocalProvider(json_response=json_response), system_prompt="test system"
    )


_VALID_JUDGE_RESPONSE = {
    "best_plan_id": "plan_1",
    "confidence": 0.8,
    "main_reason": "Plan 1 directly answers the air threat.",
    "why_not_others": [],
    "final_actions": [{"type": "buy_unit", "unit": "arclight", "x": None, "y": None}],
    "placement": [{"unit": "arclight", "x": 0, "y": -100, "action": "new"}],
    "watch_next_round": ["Monitor if enemy adds more air."],
    "mistake_to_avoid": "Don't skip anti-air.",
}


# ── Happy path ────────────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_returns_judge_output():
    judge = _make_judge(_VALID_JUDGE_RESPONSE)
    plans = [(_make_plan(), _valid_result())]
    result = await judge.select_plan(_make_state(), _no_features(), plans)
    assert isinstance(result, JudgeOutput)
    assert result.best_plan_id == "plan_1"


@pytest.mark.anyio
async def test_confidence_propagated():
    judge = _make_judge(_VALID_JUDGE_RESPONSE)
    result = await judge.select_plan(
        _make_state(), _no_features(), [(_make_plan(), _valid_result())]
    )
    assert result.confidence == pytest.approx(0.8)


@pytest.mark.anyio
async def test_placement_stripped_from_judge_output():
    """Judge must not own placement — LLM placement is always stripped."""
    judge = _make_judge(_VALID_JUDGE_RESPONSE)
    result = await judge.select_plan(
        _make_state(), _no_features(), [(_make_plan(), _valid_result())]
    )
    assert result.placement == []


@pytest.mark.anyio
async def test_watch_next_round_populated():
    judge = _make_judge(_VALID_JUDGE_RESPONSE)
    result = await judge.select_plan(
        _make_state(), _no_features(), [(_make_plan(), _valid_result())]
    )
    assert "Monitor if enemy adds more air." in result.watch_next_round


@pytest.mark.anyio
async def test_mistake_to_avoid_populated():
    judge = _make_judge(_VALID_JUDGE_RESPONSE)
    result = await judge.select_plan(
        _make_state(), _no_features(), [(_make_plan(), _valid_result())]
    )
    assert result.mistake_to_avoid == "Don't skip anti-air."


# ── Fallback behaviour ────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_fallback_on_provider_exception():
    class FailingProvider:
        async def complete_json(self, _system, _user, schema=None, temperature=0.2):
            raise RuntimeError("timeout")

        def stream_text(self, _system, _user, temperature=0.2):
            async def _gen():
                yield ""

            return _gen()

    judge = Judge(FailingProvider(), system_prompt="test")
    plans = [(_make_plan("plan_a"), _valid_result("plan_a"))]
    result = await judge.select_plan(_make_state(), _no_features(), plans)
    assert result.best_plan_id == "plan_a"


@pytest.mark.anyio
async def test_fallback_on_invalid_json_shape():
    judge = _make_judge({"wrong_key": "oops"})
    plans = [(_make_plan("plan_b"), _valid_result("plan_b"))]
    result = await judge.select_plan(_make_state(), _no_features(), plans)
    assert result.best_plan_id == "plan_b"


def test_fallback_selects_valid_plan_first():
    """Fallback prefers valid plans over invalid ones."""
    plans = [
        (_make_plan("plan_invalid"), _invalid_result("plan_invalid")),
        (_make_plan("plan_valid"), _valid_result("plan_valid")),
    ]
    result = _make_fallback_judge_output(plans)
    assert result.best_plan_id == "plan_valid"


def test_fallback_with_no_plans():
    result = _make_fallback_judge_output([])
    assert result.best_plan_id == "plan_fallback"
    assert result.confidence == 0.0


def test_fallback_returns_judge_output_instance():
    result = _make_fallback_judge_output([(_make_plan(), _valid_result())])
    assert isinstance(result, JudgeOutput)


# ── LLM contract enforcement ─────────────────────────────────────────────────


@pytest.mark.anyio
async def test_judge_cannot_select_invalid_plan():
    """If LLM selects a plan with validation errors, fall back to a valid one."""
    response = dict(_VALID_JUDGE_RESPONSE)
    response["best_plan_id"] = "plan_invalid"

    judge = _make_judge(response)
    plans = [
        (_make_plan("plan_invalid"), _invalid_result("plan_invalid")),
        (_make_plan("plan_valid"), _valid_result("plan_valid")),
    ]
    result = await judge.select_plan(_make_state(), _no_features(), plans)
    assert result.best_plan_id == "plan_valid"
    assert result.best_plan_id != "plan_invalid"


# ── why_not_others handling ───────────────────────────────────────────────────


@pytest.mark.anyio
async def test_why_not_others_parsed():
    response = dict(_VALID_JUDGE_RESPONSE)
    response["why_not_others"] = [{"plan_id": "plan_2", "reason": "Too greedy."}]
    judge = _make_judge(response)
    result = await judge.select_plan(
        _make_state(), _no_features(), [(_make_plan(), _valid_result())]
    )
    assert len(result.why_not_others) == 1
    assert result.why_not_others[0].plan_id == "plan_2"
    assert result.why_not_others[0].reason == "Too greedy."


# ── Integration with parsed_replay fixture ────────────────────────────────────


@pytest.mark.anyio
async def test_judge_from_parsed_replay(parsed_replay):
    builder = StateViewBuilder()
    extractor = FeatureExtractor()
    gen = LegalActionGenerator()
    validator = PlanValidator()

    state = builder.build(parsed_replay, supply=200, player_name="Player1")
    features = extractor.extract(state)
    legal_actions, _groups = gen.generate(state, features)

    plan = _make_fallback_plan(state)
    result = validator.validate_placement(plan.placement, state, legal_actions)
    validated_plans = [(plan, result)]

    judge_response = {
        "best_plan_id": "plan_fallback",
        "confidence": 0.5,
        "main_reason": "Only plan available.",
        "why_not_others": [],
        "final_actions": [],
        "placement": plan.placement,
        "watch_next_round": [],
        "mistake_to_avoid": "",
    }
    judge = Judge(LocalProvider(json_response=judge_response), system_prompt="test")
    result_out = await judge.select_plan(state, features, validated_plans)
    assert result_out.best_plan_id == "plan_fallback"
    assert isinstance(result_out, JudgeOutput)
