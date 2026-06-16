"""Tests for PlanScorer (Phase 5)."""

from mechabellum_replay_parser.coach.plan_scorer import PlanScorer
from mechabellum_replay_parser.coach.schemas import (
    ArmyProfile,
    AnswerStrength,
    CandidatePlan,
    PlayerRoundView,
    PlanScoreBreakdown,
    PlanValidationResult,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ThreatSignal,
    ThreatUrgency,
    ValidationIssue,
)


# ── Fixtures / helpers ────────────────────────────────────────────────────────


def _make_plan(
    plan_id: str,
    action_ids: list[str] | None = None,
    total_cost: int = 0,
) -> CandidatePlan:
    return CandidatePlan(
        id=plan_id,
        title=plan_id,
        action_ids=action_ids or [],
        total_cost=total_cost,
        main_goal="test",
        why_it_works="test",
        risks=[],
        expected_enemy_response=[],
        confidence=0.5,
    )


def _valid_result(plan_id: str) -> PlanValidationResult:
    return PlanValidationResult(plan_id=plan_id, is_valid=True, issues=[])


def _invalid_result(plan_id: str) -> PlanValidationResult:
    return PlanValidationResult(
        plan_id=plan_id,
        is_valid=False,
        issues=[
            ValidationIssue(severity="error", code="INVALID_ACTION", message="Action not allowed")
        ],
    )


def _make_features(
    threats: list[ThreatSignal] | None = None,
    tower_notes: list[str] | None = None,
    tempo_state: str = "even",
) -> TacticalFeatures:
    return TacticalFeatures(
        threats=threats or [],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state=tempo_state,
        board_posture="standard",
        tower_notes=tower_notes or [],
        likely_enemy_continuation=[],
        priority_questions=[],
        my_army_profile=ArmyProfile(),
        enemy_army_profile=ArmyProfile(),
    )


def _make_state(supply: int = 600) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=3,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=supply,
        my_state=PlayerRoundView(
            name="Me",
            army_value=500,
            shop=ShopView(buys_remaining=4, unlocks_remaining=1),
        ),
        enemy_states=[PlayerRoundView(name="Enemy", army_value=500)],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _air_threat(answer: AnswerStrength = AnswerStrength.NONE) -> ThreatSignal:
    return ThreatSignal(
        key="enemy_air_pressure",
        severity=0.9,
        urgency=ThreatUrgency.CRITICAL,
        source_units=["phoenix"],
        my_answer=answer,
        recommended_response_types=["add_anti_air", "upgrade_anti_air"],
        bad_response_types=["more_ground_chaff"],
    )


# ── Test 1: Invalid plan gets full legality penalty ────────────────────────────


def test_invalid_plan_gets_full_legality_penalty():
    plan = _make_plan("plan_x", action_ids=["buy_arclight"], total_cost=100)
    result = _invalid_result("plan_x")
    features = _make_features()
    state = _make_state(supply=600)

    breakdown = PlanScorer().score(plan, result, features, state)

    assert breakdown.legality_penalty == 1.0
    assert breakdown.total_score == 0.0
    assert any("invalid" in w.lower() for w in breakdown.warnings)


# ── Test 2: Anti-air plan scores higher than ground-only vs air threat ─────────


def test_anti_air_plan_scores_higher_vs_air_threat():
    threat = _air_threat()
    features = _make_features(threats=[threat])
    state = _make_state(supply=600)
    scorer = PlanScorer()

    aa_plan = _make_plan("aa", action_ids=["buy_arclight"], total_cost=100)
    aa_score = scorer.score(aa_plan, _valid_result("aa"), features, state)

    ground_plan = _make_plan("ground", action_ids=["buy_fortress"], total_cost=400)
    ground_score = scorer.score(ground_plan, _valid_result("ground"), features, state)

    assert aa_score.threat_coverage > ground_score.threat_coverage
    assert aa_score.total_score > ground_score.total_score


# ── Test 3: Ground-only scores 0 threat coverage vs urgent air threat ──────────


def test_ground_only_scores_zero_threat_coverage_vs_air_threat():
    threat = _air_threat()
    features = _make_features(threats=[threat])
    state = _make_state(supply=600)

    plan = _make_plan("ground", action_ids=["buy_fortress", "keep_rhino_0"], total_cost=400)
    breakdown = PlanScorer().score(plan, _valid_result("ground"), features, state)

    assert breakdown.threat_coverage == 0.0


# ── Test 4: Tower-defense plan scores higher when tower exposed ────────────────


def test_tower_defense_scores_higher_with_tower_exposure():
    features = _make_features(
        tower_notes=["tower_exposure_right: supply_tower at x=150 may be flanked."]
    )
    state = _make_state(supply=600)
    scorer = PlanScorer()

    reposition_plan = _make_plan(
        "td", action_ids=["keep_fortress_0", "move_crawler_0"], total_cost=0
    )
    td_score = scorer.score(reposition_plan, _valid_result("td"), features, state)

    no_reposition_plan = _make_plan("no_td", action_ids=["buy_arclight"], total_cost=100)
    no_td_score = scorer.score(no_reposition_plan, _valid_result("no_td"), features, state)

    assert td_score.tower_protection > no_td_score.tower_protection


# ── Test 5: Overspend (cost > supply) scores 0 supply_efficiency ──────────────


def test_overspend_scores_zero_supply_efficiency():
    features = _make_features()
    state = _make_state(supply=200)

    overspend_plan = _make_plan("over", action_ids=["buy_fortress"], total_cost=500)
    breakdown = PlanScorer().score(overspend_plan, _valid_result("over"), features, state)

    assert breakdown.supply_efficiency == 0.0
    assert any("verspend" in w or ">" in w for w in breakdown.warnings)


def test_within_supply_scores_higher_than_overspend():
    features = _make_features()
    state = _make_state(supply=400)
    scorer = PlanScorer()

    good_plan = _make_plan("good", action_ids=["buy_arclight"], total_cost=100)
    good_score = scorer.score(good_plan, _valid_result("good"), features, state)

    overspend_plan = _make_plan("over", action_ids=["buy_fortress"], total_cost=600)
    over_score = scorer.score(overspend_plan, _valid_result("over"), features, state)

    assert good_score.supply_efficiency > over_score.supply_efficiency
    assert good_score.total_score > over_score.total_score


# ── Test 6: total_score is always clamped to [0, 1] ───────────────────────────


def test_total_score_clamped_zero_to_one():
    scorer = PlanScorer()
    # invalid plan with zero supply — could produce very negative raw score
    plan = _make_plan("bad", action_ids=[], total_cost=9999)
    result = _invalid_result("bad")
    features = _make_features()
    state = _make_state(supply=0)

    breakdown = scorer.score(plan, result, features, state)
    assert 0.0 <= breakdown.total_score <= 1.0


def test_total_score_clamped_valid_good_plan():
    scorer = PlanScorer()
    # An ideal-looking plan should not exceed 1.0
    plan = _make_plan("ideal", action_ids=["buy_arclight"], total_cost=100)
    result = _valid_result("ideal")
    features = _make_features(threats=[_air_threat()])
    state = _make_state(supply=600)

    breakdown = scorer.score(plan, result, features, state)
    assert 0.0 <= breakdown.total_score <= 1.0


# ── Test 7: score_all returns one breakdown per plan ──────────────────────────


def test_score_all_returns_one_per_plan():
    scorer = PlanScorer()
    plans = [
        (_make_plan(f"p{i}", action_ids=[], total_cost=0), _valid_result(f"p{i}"))
        for i in range(4)
    ]
    features = _make_features()
    state = _make_state()

    breakdowns = scorer.score_all(plans, features, state)
    assert len(breakdowns) == 4
    assert all(isinstance(b, PlanScoreBreakdown) for b in breakdowns)
    assert [b.plan_id for b in breakdowns] == ["p0", "p1", "p2", "p3"]


# ── Test 8: Tempo-behind plan with buys scores better on tempo ────────────────


def test_tempo_behind_with_buys_scores_higher_tempo():
    scorer = PlanScorer()
    features_behind = _make_features(tempo_state="behind")
    state = _make_state(supply=600)

    buy_plan = _make_plan("buy", action_ids=["buy_arclight"], total_cost=100)
    no_buy_plan = _make_plan("keep", action_ids=["keep_fortress_0"], total_cost=0)

    buy_score = scorer.score(buy_plan, _valid_result("buy"), features_behind, state)
    no_buy_score = scorer.score(no_buy_plan, _valid_result("keep"), features_behind, state)

    assert buy_score.tempo > no_buy_score.tempo
