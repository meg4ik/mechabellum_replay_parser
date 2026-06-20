from __future__ import annotations

import json

from mechabellum_replay_parser.coach.influence_schemas import (
    InfluenceAnalysisSummary,
    InfluenceGridSpec,
    MapZone,
    TacticalInfluenceFinding,
    ZoneInfluenceSummary,
)
from mechabellum_replay_parser.coach.planner import _compact_state
from mechabellum_replay_parser.coach.judge import _build_user
from mechabellum_replay_parser.coach.schemas import (
    ArmyProfile,
    CandidatePlan,
    PlayerRoundView,
    PlanScoreBreakdown,
    PlanValidationResult,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
)


def _grid() -> InfluenceGridSpec:
    return InfluenceGridSpec(x_min=-300, x_max=300, y_front=-10, y_back=-310, width=30, height=20, player_side="negative_y")


def _state() -> StateView:
    return StateView(
        match_mode="VS_1_1", round=4, player_name="Me", enemy_names=["Enemy"],
        my_supply=600,
        my_state=PlayerRoundView(name="Me", army_value=500, shop=ShopView(buys_remaining=3, unlocks_remaining=1)),
        enemy_states=[PlayerRoundView(name="Enemy", army_value=500)],
        recent_rounds=[], strategic_memory=StrategicMemory(),
    )


def _features(threats=None) -> TacticalFeatures:
    return TacticalFeatures(
        threats=threats or [], my_weaknesses=[], enemy_weaknesses=[],
        tempo_state="even", board_posture="standard",
        tower_notes=[], likely_enemy_continuation=[], priority_questions=[],
        my_army_profile=ArmyProfile(), enemy_army_profile=ArmyProfile(),
    )


def _finding(key="anti_air_gap", severity=0.8) -> TacticalInfluenceFinding:
    return TacticalInfluenceFinding(
        key=key, severity=severity, zone=MapZone.RIGHT_FRONT,
        evidence="Test evidence.", recommended_response_types=["add_anti_air"],
    )


def _influence(findings=None) -> InfluenceAnalysisSummary:
    return InfluenceAnalysisSummary(
        grid=_grid(),
        global_assessment={"ground_balance": "enemy_favored"},
        zones=[ZoneInfluenceSummary(zone=z) for z in MapZone],
        tactical_findings=findings or [],
    )


def _plan(plan_id="p1") -> CandidatePlan:
    return CandidatePlan(
        id=plan_id, title="test", action_ids=["buy_arclight"],
        total_cost=100, main_goal="test", why_it_works="test",
        risks=[], expected_enemy_response=[], confidence=0.5,
    )


def _valid(plan_id="p1") -> PlanValidationResult:
    return PlanValidationResult(plan_id=plan_id, is_valid=True, issues=[])


def _score(plan_id="p1", influence_imp=0.7) -> PlanScoreBreakdown:
    return PlanScoreBreakdown(
        plan_id=plan_id, total_score=0.7, threat_coverage=0.8,
        supply_efficiency=0.6, tempo=0.5, scaling=0.3,
        positioning_safety=0.6, tower_protection=0.5,
        flexibility_next_round=0.8, overreaction_risk=0.0,
        legality_penalty=0.0,
        influence_improvement=influence_imp,
        anti_air_improvement=0.5, anti_chaff_improvement=0.0,
        anti_heavy_improvement=0.0, artillery_risk_reduction=0.0,
        influence_explanation=["Addresses anti-air gap (severity 0.80) in right_front."],
    )


# ── Planner: influence_analysis injected ─────────────────────────────────────


def test_planner_compact_state_includes_influence():
    influence = _influence(findings=[_finding()])
    result = _compact_state(_state(), _features(), [], [], influence=influence)
    data = json.loads(result)
    assert "influence_analysis" in data
    assert "tactical_findings" in data["influence_analysis"]
    assert len(data["influence_analysis"]["tactical_findings"]) == 1
    assert data["influence_analysis"]["tactical_findings"][0]["key"] == "anti_air_gap"


def test_planner_compact_state_without_influence():
    result = _compact_state(_state(), _features(), [], [])
    data = json.loads(result)
    assert "influence_analysis" not in data


def test_planner_compact_state_empty_findings_not_injected():
    influence = _influence(findings=[])
    result = _compact_state(_state(), _features(), [], [], influence=influence)
    data = json.loads(result)
    assert "influence_analysis" not in data


def test_planner_influence_has_global_assessment():
    influence = _influence(findings=[_finding()])
    result = _compact_state(_state(), _features(), [], [], influence=influence)
    data = json.loads(result)
    assert data["influence_analysis"]["global_assessment"]["ground_balance"] == "enemy_favored"


def test_planner_influence_has_critical_zones():
    influence = _influence(findings=[_finding()])
    result = _compact_state(_state(), _features(), [], [], influence=influence)
    data = json.loads(result)
    assert "critical_zones" in data["influence_analysis"]


def test_planner_influence_finding_has_zone():
    influence = _influence(findings=[_finding()])
    result = _compact_state(_state(), _features(), [], [], influence=influence)
    data = json.loads(result)
    f = data["influence_analysis"]["tactical_findings"][0]
    assert f["zone"] == "right_front"
    assert f["severity"] == 0.8
    assert "add_anti_air" in f["recommended_response_types"]


# ── Judge: influence_analysis + scores injected ──────────────────────────────


def test_judge_build_user_includes_influence():
    influence = _influence(findings=[_finding()])
    plans = [(_plan(), _valid())]
    scores = [_score()]
    result = _build_user(_state(), _features(), plans, [], scores, influence=influence)
    data = json.loads(result)
    assert "influence_analysis" in data
    assert len(data["influence_analysis"]["tactical_findings"]) == 1


def test_judge_build_user_without_influence():
    plans = [(_plan(), _valid())]
    result = _build_user(_state(), _features(), plans, [])
    data = json.loads(result)
    assert "influence_analysis" not in data


def test_judge_plan_score_includes_influence_fields():
    influence = _influence(findings=[_finding()])
    plans = [(_plan(), _valid())]
    scores = [_score(influence_imp=0.7)]
    result = _build_user(_state(), _features(), plans, [], scores, influence=influence)
    data = json.loads(result)
    plan_data = data["candidate_plans"][0]
    assert "score" in plan_data
    assert plan_data["score"]["influence_improvement"] == 0.7
    assert plan_data["score"]["anti_air_improvement"] == 0.5
    assert "influence_explanation" in plan_data["score"]


def test_judge_plan_score_no_influence_fields_when_zero():
    plans = [(_plan(), _valid())]
    scores = [PlanScoreBreakdown(
        plan_id="p1", total_score=0.5, threat_coverage=0.5,
        supply_efficiency=0.5, tempo=0.5, scaling=0.3,
        positioning_safety=0.5, tower_protection=0.5,
        flexibility_next_round=0.5, overreaction_risk=0.0,
        legality_penalty=0.0,
    )]
    result = _build_user(_state(), _features(), plans, [], scores)
    data = json.loads(result)
    plan_data = data["candidate_plans"][0]
    assert "influence_improvement" not in plan_data.get("score", {})


# ── No raw arrays in LLM data ───────────────────────────────────────────────


def test_no_numpy_or_raw_arrays_in_planner_data():
    influence = _influence(findings=[_finding()])
    result = _compact_state(_state(), _features(), [], [], influence=influence)
    assert "numpy" not in result.lower()
    assert "ndarray" not in result.lower()
    data = json.loads(result)
    assert isinstance(data, dict)


def test_no_numpy_or_raw_arrays_in_judge_data():
    influence = _influence(findings=[_finding()])
    plans = [(_plan(), _valid())]
    scores = [_score()]
    result = _build_user(_state(), _features(), plans, [], scores, influence=influence)
    assert "numpy" not in result.lower()
    assert "ndarray" not in result.lower()


# ── Prompt files updated ─────────────────────────────────────────────────────


def test_planner_prompt_mentions_influence():
    from pathlib import Path
    prompt_path = Path(__file__).parent.parent / "src" / "mechabellum_replay_parser" / "prompts" / "planner_v1.md"
    content = prompt_path.read_text(encoding="utf-8")
    assert "influence" in content.lower()
    assert "tactical_findings" in content


def test_judge_prompt_mentions_influence():
    from pathlib import Path
    prompt_path = Path(__file__).parent.parent / "src" / "mechabellum_replay_parser" / "prompts" / "judge_v1.md"
    content = prompt_path.read_text(encoding="utf-8")
    assert "influence" in content.lower()
    assert "influence_improvement" in content
