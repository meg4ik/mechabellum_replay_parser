"""Tests for EvalRubric scoring (Phase 7)."""

from mechabellum_replay_parser.eval.rubric import EvalRubric, RubricScores
from mechabellum_replay_parser.eval.cases import EvalCase, EvalExpected
from mechabellum_replay_parser.coach.schemas import (
    CandidatePlan,
    PlanScoreBreakdown,
    PlanValidationResult,
    PlayerRoundView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ThreatSignal,
    ValidationIssue,
)


def _make_state_view(round_: int = 1) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=round_,
        player_name="P",
        enemy_names=["E"],
        my_state=PlayerRoundView(name="P"),
        enemy_states=[PlayerRoundView(name="E")],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _make_features(threat_keys: list[str]) -> TacticalFeatures:
    threats = [ThreatSignal(key=k, severity=0.7) for k in threat_keys]
    return TacticalFeatures(
        threats=threats,
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state="even",
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
    )


def _make_breakdown(
    plan_id: str = "p1",
    total_score: float = 0.5,
    supply_efficiency: float = 0.6,
    positioning_safety: float = 0.7,
    flexibility_next_round: float = 0.8,
) -> PlanScoreBreakdown:
    return PlanScoreBreakdown(
        plan_id=plan_id,
        total_score=total_score,
        threat_coverage=0.5,
        supply_efficiency=supply_efficiency,
        tempo=0.5,
        scaling=0.5,
        positioning_safety=positioning_safety,
        tower_protection=0.5,
        flexibility_next_round=flexibility_next_round,
        overreaction_risk=0.0,
        legality_penalty=0.0,
    )


def _valid_plan_pair(plan_id: str = "p1") -> tuple:
    plan = CandidatePlan(
        id=plan_id,
        title="test plan",
        action_ids=[],
        total_cost=0,
        main_goal="test",
        why_it_works="test",
        risks=[],
        expected_enemy_response=[],
        placement=[],
        confidence=0.5,
    )
    result = PlanValidationResult(plan_id=plan_id, is_valid=True, issues=[])
    return plan, result


def _invalid_plan_pair(plan_id: str = "p1") -> tuple:
    plan = CandidatePlan(
        id=plan_id,
        title="bad plan",
        action_ids=[],
        total_cost=9999,
        main_goal="test",
        why_it_works="test",
        risks=[],
        expected_enemy_response=[],
        placement=[],
        confidence=0.5,
    )
    result = PlanValidationResult(
        plan_id=plan_id,
        is_valid=False,
        issues=[ValidationIssue(severity="error", code="OVER_BUDGET", message="too expensive")],
    )
    return plan, result


def _make_case(threats: list[str]) -> EvalCase:
    return EvalCase(
        name="test_case",
        state_view=_make_state_view(),
        expected=EvalExpected(must_address_threats=threats),
    )


# ── RubricScores model ────────────────────────────────────────────────────────


def test_rubric_scores_fields():
    s = RubricScores(
        legality=1,
        main_threat_answered=4,
        supply_efficiency=3,
        positioning=2,
        next_round_flexibility=3,
        explanation_quality=3,
        total=20.0,
    )
    assert s.legality == 1
    assert s.total == 20.0
    assert not s.notes


def test_rubric_scores_with_notes():
    s = RubricScores(
        legality=0,
        main_threat_answered=0,
        supply_efficiency=0,
        positioning=0,
        next_round_flexibility=0,
        explanation_quality=3,
        total=3.0,
        notes=["No valid plans."],
    )
    assert "No valid plans." in s.notes


# ── legality dimension ────────────────────────────────────────────────────────


def test_legality_one_when_any_valid_plan():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    scores = rubric.score_case(case, features, [], [_make_breakdown()], [_valid_plan_pair()])
    assert scores.legality == 1


def test_legality_zero_when_no_valid_plans():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    scores = rubric.score_case(case, features, [], [], [_invalid_plan_pair()])
    assert scores.legality == 0
    assert any("valid" in n.lower() for n in scores.notes)


def test_legality_one_when_at_least_one_valid_among_mixed():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    validated = [_invalid_plan_pair("p1"), _valid_plan_pair("p2")]
    scores = rubric.score_case(case, features, [], [_make_breakdown("p2")], validated)
    assert scores.legality == 1


# ── main_threat_answered dimension ───────────────────────────────────────────


def test_all_threats_detected_gives_five():
    rubric = EvalRubric()
    case = _make_case(["enemy_air_pressure"])
    features = _make_features(["enemy_air_pressure"])
    scores = rubric.score_case(case, features, [], [_make_breakdown()], [_valid_plan_pair()])
    assert scores.main_threat_answered == 5


def test_no_threats_required_gives_five():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features(["something_irrelevant"])
    scores = rubric.score_case(case, features, [], [_make_breakdown()], [_valid_plan_pair()])
    assert scores.main_threat_answered == 5


def test_half_threats_detected_gives_two():
    rubric = EvalRubric()
    case = _make_case(["threat_a", "threat_b"])
    features = _make_features(["threat_a"])  # only 1 of 2
    scores = rubric.score_case(case, features, [], [_make_breakdown()], [_valid_plan_pair()])
    # int(5 * 1/2) == 2
    assert scores.main_threat_answered == 2


def test_zero_threats_detected_gives_zero():
    rubric = EvalRubric()
    case = _make_case(["threat_a"])
    features = _make_features(["different_threat"])
    scores = rubric.score_case(case, features, [], [_make_breakdown()], [_valid_plan_pair()])
    assert scores.main_threat_answered == 0
    assert any("not detected" in n for n in scores.notes)


# ── supply/positioning/flexibility from best PlanScoreBreakdown ───────────────


def test_supply_efficiency_derived_from_best_breakdown():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    bd = [_make_breakdown(supply_efficiency=0.8)]  # int(0.8*5) == 4
    scores = rubric.score_case(case, features, [], bd, [_valid_plan_pair()])
    assert scores.supply_efficiency == 4


def test_positioning_derived_from_best_breakdown():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    bd = [_make_breakdown(positioning_safety=1.0)]  # int(1.0*5) == 5
    scores = rubric.score_case(case, features, [], bd, [_valid_plan_pair()])
    assert scores.positioning == 5


def test_flexibility_derived_from_best_breakdown():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    bd = [_make_breakdown(flexibility_next_round=0.0)]
    scores = rubric.score_case(case, features, [], bd, [_valid_plan_pair()])
    assert scores.next_round_flexibility == 0


def test_uses_best_breakdown_not_worst():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    validated = [_valid_plan_pair("p1"), _valid_plan_pair("p2")]
    bd = [
        _make_breakdown("p1", total_score=0.2, supply_efficiency=0.2),
        _make_breakdown("p2", total_score=0.9, supply_efficiency=0.9),
    ]
    scores = rubric.score_case(case, features, [], bd, validated)
    assert scores.supply_efficiency == 4  # int(0.9*5)


def test_zeros_when_no_score_breakdowns():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    scores = rubric.score_case(case, features, [], [], [_valid_plan_pair()])
    assert scores.supply_efficiency == 0
    assert scores.positioning == 0
    assert scores.next_round_flexibility == 0


# ── explanation_quality ───────────────────────────────────────────────────────


def test_explanation_quality_always_three():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    scores = rubric.score_case(case, features, [], [_make_breakdown()], [_valid_plan_pair()])
    assert scores.explanation_quality == 3


# ── total ─────────────────────────────────────────────────────────────────────


def test_total_correct_for_perfect_scenario():
    rubric = EvalRubric()
    case = _make_case([])
    features = _make_features([])
    bd = [_make_breakdown(supply_efficiency=1.0, positioning_safety=1.0, flexibility_next_round=1.0)]
    scores = rubric.score_case(case, features, [], bd, [_valid_plan_pair()])
    # legality*5=5 + threats=5 + supply=5 + pos=5 + flex=5 + explanation=3 = 28
    assert scores.total == 28.0


def test_total_minimum_with_no_valid_plans_and_no_threats():
    rubric = EvalRubric()
    case = _make_case(["unseen_threat"])
    features = _make_features([])
    scores = rubric.score_case(case, features, [], [], [_invalid_plan_pair()])
    # legality=0, threats=0, supply=0, pos=0, flex=0, explanation=3 → total=3
    assert scores.total == 3.0
