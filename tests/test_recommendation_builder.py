"""Tests for RecommendationBuilder."""

import pytest

from mechabellum_replay_parser.coach.recommendation_builder import RecommendationBuilder
from mechabellum_replay_parser.coach.schemas import (
    CandidatePlan,
    CoachRecommendation,
    JudgeOutput,
    PlayerRoundView,
    PlanValidationResult,
    RejectedPlan,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ThreatSignal,
)


def _make_state(round_: int = 3, player: str = "Me") -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=round_,
        player_name=player,
        enemy_names=["Enemy"],
        my_supply=300,
        my_state=PlayerRoundView(name=player, army_value=600),
        enemy_states=[PlayerRoundView(name="Enemy", army_value=700)],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _features_with_threat() -> TacticalFeatures:
    return TacticalFeatures(
        threats=[
            ThreatSignal(
                key="enemy_air_pressure",
                severity=0.8,
                source_units=["phoenix"],
                explanation="Enemy has phoenix.",
                my_answer="none",
            )
        ],
        my_weaknesses=["no anti-air"],
        enemy_weaknesses=[],
        tempo_state="behind",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=["Enemy continues air investment."],
        priority_questions=[],
    )


def _make_plan(plan_id: str = "plan_aa") -> CandidatePlan:
    return CandidatePlan(
        id=plan_id,
        title="Buy arclight counter air",
        action_ids=["buy_arclight"],
        total_cost=100,
        main_goal="Stabilize against enemy air.",
        why_it_works="Arclight directly counters Phoenix.",
        risks=["Leaves less supply for army value."],
        expected_enemy_response=["Enemy adds more air."],
        placement=[{"unit": "arclight", "x": 0, "y": -100, "action": "new"}],
        confidence=0.75,
    )


def _make_judge(plan_id: str = "plan_aa") -> JudgeOutput:
    return JudgeOutput(
        best_plan_id=plan_id,
        confidence=0.78,
        main_reason="Arclight directly counters the Phoenix threat.",
        why_not_others=[RejectedPlan(plan_id="plan_other", reason="Too greedy.")],
        final_actions=[{"type": "buy_unit", "unit": "arclight", "x": None, "y": None}],
        placement=[{"unit": "arclight", "x": 0, "y": -100, "action": "new"}],
        watch_next_round=["Watch for more air units from enemy."],
        mistake_to_avoid="Do not skip anti-air this round.",
    )


def _valid_result() -> PlanValidationResult:
    return PlanValidationResult(plan_id="plan_aa", is_valid=True, issues=[])


@pytest.fixture
def builder() -> RecommendationBuilder:
    return RecommendationBuilder()


# ── Return type ───────────────────────────────────────────────────────────────


def test_returns_coach_recommendation(builder):
    state = _make_state()
    features = _features_with_threat()
    judge = _make_judge()
    plan = _make_plan()
    result = builder.build(judge, [(plan, _valid_result())], features, state)
    assert isinstance(result, CoachRecommendation)


# ── Summary / confidence ──────────────────────────────────────────────────────


def test_summary_from_judge_reason(builder):
    state = _make_state()
    features = _features_with_threat()
    judge = _make_judge()
    result = builder.build(judge, [(_make_plan(), _valid_result())], features, state)
    assert result.summary == "Arclight directly counters the Phoenix threat."


def test_confidence_from_judge(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(),
    )
    assert result.confidence == pytest.approx(0.78)


# ── Placement ─────────────────────────────────────────────────────────────────


def test_placement_from_judge_output(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(),
    )
    assert len(result.placement) == 1
    assert result.placement[0]["unit"] == "arclight"


def test_placement_falls_back_to_plan_when_judge_empty(builder):
    judge = JudgeOutput(
        best_plan_id="plan_aa",
        confidence=0.5,
        main_reason="test",
        placement=[],  # empty judge placement
        watch_next_round=[],
        mistake_to_avoid="",
    )
    result = builder.build(
        judge, [(_make_plan(), _valid_result())], _features_with_threat(), _make_state()
    )
    # Falls back to plan.placement
    assert len(result.placement) >= 1


# ── Threats / risks / watch ───────────────────────────────────────────────────


def test_main_threats_from_features(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(),
    )
    assert "enemy_air_pressure" in result.main_threats


def test_no_low_severity_threat_in_main_threats(builder):
    features = TacticalFeatures(
        threats=[
            ThreatSignal(
                key="minor_issue",
                severity=0.3,  # below 0.5 threshold
                source_units=[],
                explanation="minor",
                my_answer="strong",
            )
        ],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )
    result = builder.build(
        _make_judge(), [(_make_plan(), _valid_result())], features, _make_state()
    )
    assert "minor_issue" not in result.main_threats


def test_risks_from_selected_plan(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(),
    )
    assert "Leaves less supply for army value." in result.risks


def test_watch_next_round_from_judge(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(),
    )
    assert "Watch for more air units from enemy." in result.watch_next_round


# ── Coach text ────────────────────────────────────────────────────────────────


def test_coach_text_contains_round_and_player(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(round_=5, player="Alice"),
    )
    assert "Round 5" in result.coach_text
    assert "Alice" in result.coach_text


def test_coach_text_contains_decision(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(),
    )
    assert "Arclight directly counters the Phoenix threat." in result.coach_text


def test_coach_text_contains_mistake(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(),
    )
    assert "Do not skip anti-air this round." in result.coach_text


def test_coach_text_nonempty(builder):
    result = builder.build(
        _make_judge(),
        [(_make_plan(), _valid_result())],
        _features_with_threat(),
        _make_state(),
    )
    assert len(result.coach_text) > 50


# ── Validation field ──────────────────────────────────────────────────────────


def test_validation_attached(builder):
    val = _valid_result()
    result = builder.build(
        _make_judge(), [(_make_plan(), val)], _features_with_threat(), _make_state()
    )
    assert result.validation is not None
    assert result.validation.is_valid is True


# ── Fallback when plan not found ──────────────────────────────────────────────


def test_fallback_to_first_plan_when_id_not_found(builder):
    judge = JudgeOutput(
        best_plan_id="plan_nonexistent",
        confidence=0.5,
        main_reason="selected unknown id",
        placement=[{"unit": "crawler", "x": 0, "y": -100, "action": "keep"}],
        watch_next_round=[],
        mistake_to_avoid="",
    )
    plan = _make_plan("plan_real")
    result = builder.build(
        judge, [(plan, _valid_result())], _features_with_threat(), _make_state()
    )
    # Should not crash; falls back to first plan for risks
    assert isinstance(result, CoachRecommendation)
