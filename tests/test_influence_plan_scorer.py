from __future__ import annotations

from mechabellum_replay_parser.coach.influence_schemas import (
    InfluenceAnalysisSummary,
    InfluenceGridSpec,
    MapZone,
    TacticalInfluenceFinding,
    ZoneInfluenceSummary,
)
from mechabellum_replay_parser.coach.plan_scorer import PlanScorer
from mechabellum_replay_parser.coach.schemas import (
    ArmyProfile,
    AnswerStrength,
    CandidatePlan,
    PlayerRoundView,
    PlanValidationResult,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ThreatSignal,
    ThreatUrgency,
    ValidationIssue,
)


def _make_plan(plan_id: str, action_ids: list[str] | None = None, total_cost: int = 200) -> CandidatePlan:
    return CandidatePlan(
        id=plan_id, title=plan_id,
        action_ids=action_ids or [],
        total_cost=total_cost,
        main_goal="test", why_it_works="test",
        risks=[], expected_enemy_response=[],
        confidence=0.5,
    )


def _valid(plan_id: str) -> PlanValidationResult:
    return PlanValidationResult(plan_id=plan_id, is_valid=True, issues=[])


def _invalid(plan_id: str) -> PlanValidationResult:
    return PlanValidationResult(
        plan_id=plan_id, is_valid=False,
        issues=[ValidationIssue(severity="error", code="X", message="x")],
    )


def _features(threats: list[ThreatSignal] | None = None, tempo: str = "even") -> TacticalFeatures:
    return TacticalFeatures(
        threats=threats or [],
        my_weaknesses=[], enemy_weaknesses=[],
        tempo_state=tempo, board_posture="standard",
        tower_notes=[], likely_enemy_continuation=[],
        priority_questions=[],
        my_army_profile=ArmyProfile(), enemy_army_profile=ArmyProfile(),
    )


def _state(supply: int = 600) -> StateView:
    return StateView(
        match_mode="VS_1_1", round=3, player_name="Me", enemy_names=["Enemy"],
        my_supply=supply,
        my_state=PlayerRoundView(name="Me", army_value=500, shop=ShopView(buys_remaining=4, unlocks_remaining=1)),
        enemy_states=[PlayerRoundView(name="Enemy", army_value=500)],
        recent_rounds=[], strategic_memory=StrategicMemory(),
    )


def _grid() -> InfluenceGridSpec:
    return InfluenceGridSpec(x_min=-300, x_max=300, y_front=-10, y_back=-310, width=30, height=20, player_side="negative_y")


def _influence(findings: list[TacticalInfluenceFinding] | None = None) -> InfluenceAnalysisSummary:
    return InfluenceAnalysisSummary(
        grid=_grid(),
        global_assessment={"ground_balance": "neutral"},
        zones=[ZoneInfluenceSummary(zone=z) for z in MapZone],
        tactical_findings=findings or [],
    )


def _air_finding(severity: float = 0.8) -> TacticalInfluenceFinding:
    return TacticalInfluenceFinding(
        key="anti_air_gap", severity=severity,
        zone=MapZone.RIGHT_FRONT,
        evidence="Enemy air high, my anti-air low.",
        recommended_response_types=["add_anti_air", "shift_anti_air"],
    )


def _heavy_finding(severity: float = 0.7) -> TacticalInfluenceFinding:
    return TacticalInfluenceFinding(
        key="anti_heavy_gap", severity=severity,
        zone=MapZone.CENTER_FRONT,
        evidence="Enemy heavy, my anti-heavy low.",
        recommended_response_types=["add_single_target", "unlock_anti_heavy"],
    )


def _air_threat() -> ThreatSignal:
    return ThreatSignal(
        key="enemy_air_pressure", severity=0.9, urgency=ThreatUrgency.CRITICAL,
        source_units=["phoenix"], my_answer=AnswerStrength.NONE,
        recommended_response_types=["add_anti_air"],
    )


# ── Backward compatibility without influence ─────────────────────────────────


def test_scorer_works_without_influence():
    scorer = PlanScorer()
    plan = _make_plan("p1", action_ids=["buy_arclight"])
    result = scorer.score(plan, _valid("p1"), _features(threats=[_air_threat()]), _state())
    assert result.total_score > 0
    assert result.influence_improvement == 0.0


def test_score_all_without_influence():
    scorer = PlanScorer()
    plans = [(_make_plan("p1"), _valid("p1")), (_make_plan("p2"), _valid("p2"))]
    results = scorer.score_all(plans, _features(), _state())
    assert len(results) == 2


# ── Influence improvement ────────────────────────────────────────────────────


def test_anti_air_plan_scores_higher_with_influence():
    scorer = PlanScorer()
    influence = _influence(findings=[_air_finding(0.8)])
    threat = _air_threat()
    feats = _features(threats=[threat])
    state = _state()

    anti_air_plan = _make_plan("aa", action_ids=["buy_arclight"])
    ground_plan = _make_plan("ground", action_ids=["buy_crawler"])

    aa_score = scorer.score(anti_air_plan, _valid("aa"), feats, state, influence)
    gnd_score = scorer.score(ground_plan, _valid("ground"), feats, state, influence)

    assert aa_score.influence_improvement > gnd_score.influence_improvement
    assert aa_score.anti_air_improvement > 0
    assert gnd_score.anti_air_improvement == 0


def test_influence_changes_ranking():
    scorer = PlanScorer()
    influence = _influence(findings=[_air_finding(0.9)])
    threat = _air_threat()
    feats = _features(threats=[threat])

    aa_plan = _make_plan("aa", action_ids=["buy_mustang"], total_cost=200)
    gnd_plan = _make_plan("gnd", action_ids=["buy_crawler"], total_cost=100)

    aa_score = scorer.score(aa_plan, _valid("aa"), feats, _state(), influence)
    gnd_score = scorer.score(gnd_plan, _valid("gnd"), feats, _state(), influence)

    assert aa_score.total_score > gnd_score.total_score


def test_anti_heavy_plan_addresses_heavy_finding():
    scorer = PlanScorer()
    influence = _influence(findings=[_heavy_finding(0.7)])
    threat = ThreatSignal(
        key="enemy_frontline_wall", severity=0.8, urgency=ThreatUrgency.HIGH,
        source_units=["fortress"], my_answer=AnswerStrength.NONE,
        recommended_response_types=["add_single_target"],
    )
    feats = _features(threats=[threat])

    anti_heavy_plan = _make_plan("ah", action_ids=["buy_marksmen"], total_cost=100)
    score = scorer.score(anti_heavy_plan, _valid("ah"), feats, _state(), influence)
    assert score.anti_heavy_improvement > 0
    assert score.influence_improvement > 0


def test_no_findings_gives_neutral_influence():
    scorer = PlanScorer()
    influence = _influence(findings=[])
    plan = _make_plan("p1", action_ids=["buy_crawler"])
    score = scorer.score(plan, _valid("p1"), _features(), _state(), influence)
    assert score.influence_improvement == 0.5


# ── Overreaction with influence ──────────────────────────────────────────────


def test_no_overreaction_penalty_when_plan_addresses_finding():
    scorer = PlanScorer()
    influence = _influence(findings=[_air_finding(0.8)])
    threat = _air_threat()
    feats = _features(threats=[threat])

    plan = _make_plan("aa", action_ids=["buy_mustang"], total_cost=400)
    score = scorer.score(plan, _valid("aa"), feats, _state(), influence)
    assert score.overreaction_risk == 0.0


# ── Invalid plans still penalized ────────────────────────────────────────────


def test_invalid_plan_still_penalized_with_influence():
    scorer = PlanScorer()
    influence = _influence(findings=[_air_finding(0.8)])
    plan = _make_plan("bad", action_ids=["buy_mustang"])
    score = scorer.score(plan, _invalid("bad"), _features(threats=[_air_threat()]), _state(), influence)
    assert score.total_score == 0.0


# ── Influence explanation populated ──────────────────────────────────────────


def test_influence_explanation_populated():
    scorer = PlanScorer()
    influence = _influence(findings=[_air_finding(0.8)])
    plan = _make_plan("aa", action_ids=["buy_arclight"])
    score = scorer.score(plan, _valid("aa"), _features(threats=[_air_threat()]), _state(), influence)
    assert len(score.influence_explanation) > 0
    assert any("anti-air" in e.lower() for e in score.influence_explanation)


# ── Multiple findings ────────────────────────────────────────────────────────


def test_multiple_findings_partially_addressed():
    scorer = PlanScorer()
    influence = _influence(findings=[_air_finding(0.8), _heavy_finding(0.6)])
    threats = [_air_threat(), ThreatSignal(
        key="enemy_frontline_wall", severity=0.6, urgency=ThreatUrgency.MEDIUM,
        source_units=["fortress"], my_answer=AnswerStrength.NONE,
        recommended_response_types=["add_single_target"],
    )]
    feats = _features(threats=threats)

    aa_only = _make_plan("aa", action_ids=["buy_arclight"])
    score = scorer.score(aa_only, _valid("aa"), feats, _state(), influence)
    assert 0 < score.influence_improvement < 1.0
    assert score.anti_air_improvement > 0
    assert score.anti_heavy_improvement == 0
