from __future__ import annotations

from mechabellum_replay_parser.coach.coordinates import CoordinateFrame
from mechabellum_replay_parser.coach.influence_analyzer import InfluenceAnalyzer
from mechabellum_replay_parser.coach.influence_map import InfluenceMapBuilder
from mechabellum_replay_parser.coach.influence_schemas import (
    InfluenceAnalysisSummary,
    MapZone,
)
from mechabellum_replay_parser.coach.schemas import (
    ArmyProfile,
    AnswerStrength,
    ConstructionView,
    ConstructionRole,
    ConstructionType,
    PlayerRoundView,
    PlayerSide,
    Position,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ThreatSignal,
    ThreatUrgency,
    UnitView,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _unit(name: str, x: int = 0, y: int = -100, level: int = 1, index: int = 0) -> UnitView:
    return UnitView(
        name=name, unit_id=0, index=index, level=level, exp=0,
        position=Position(x=x, y=y),
    )


def _state(
    my_units: list[UnitView] | None = None,
    enemy_units: list[UnitView] | None = None,
    constructions: list[ConstructionView] | None = None,
) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=4,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=600,
        my_state=PlayerRoundView(
            name="Me",
            units=my_units or [],
            constructions=constructions or [],
            shop=ShopView(buys_remaining=3, unlocks_remaining=1),
        ),
        enemy_states=[PlayerRoundView(name="Enemy", units=enemy_units or [])],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _features(
    threats: list[ThreatSignal] | None = None,
    tempo: str = "even",
) -> TacticalFeatures:
    return TacticalFeatures(
        threats=threats or [],
        my_weaknesses=[],
        enemy_weaknesses=[],
        tempo_state=tempo,
        board_posture="standard",
        tower_notes=[],
        likely_enemy_continuation=[],
        priority_questions=[],
        my_army_profile=ArmyProfile(),
        enemy_army_profile=ArmyProfile(),
    )


def _neg_frame() -> CoordinateFrame:
    return CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)


def _build_and_analyze(state, features, frame=None):
    frame = frame or _neg_frame()
    builder = InfluenceMapBuilder()
    influence = builder.build(state, frame)
    analyzer = InfluenceAnalyzer()
    return analyzer.analyze(state, features, influence)


# ── Anti-air gap ─────────────────────────────────────────────────────────────


def test_anti_air_gap_on_air_threat():
    state = _state(
        my_units=[_unit("crawler", x=0, y=-150)],
        enemy_units=[
            _unit("wasp", x=50, y=80, level=2, index=0),
            _unit("wasp", x=-50, y=80, level=2, index=1),
            _unit("wasp", x=0, y=100, level=2, index=2),
        ],
    )
    threat = ThreatSignal(
        key="enemy_air_pressure", severity=0.9, urgency=ThreatUrgency.HIGH,
        source_units=["wasp"], my_answer=AnswerStrength.NONE,
    )
    feats = _features(threats=[threat])
    summary = _build_and_analyze(state, feats)

    air_findings = [f for f in summary.tactical_findings if f.key == "anti_air_gap"]
    assert len(air_findings) > 0
    assert air_findings[0].severity > 0.2
    assert "add_anti_air" in air_findings[0].recommended_response_types


def test_no_anti_air_finding_without_air_threat():
    state = _state(
        my_units=[_unit("crawler", x=0, y=-150)],
        enemy_units=[_unit("crawler", x=0, y=150)],
    )
    feats = _features()
    summary = _build_and_analyze(state, feats)
    air_findings = [f for f in summary.tactical_findings if f.key == "anti_air_gap"]
    assert len(air_findings) == 0


# ── Anti-chaff gap ───────────────────────────────────────────────────────────


def test_anti_chaff_gap_on_chaff_flood():
    state = _state(
        my_units=[_unit("marksmen", x=0, y=-200)],
        enemy_units=[
            _unit("crawler", x=-100, y=-30, index=0),
            _unit("crawler", x=0, y=-30, index=1),
            _unit("crawler", x=100, y=-30, index=2),
            _unit("crawler", x=-50, y=-20, index=3),
            _unit("crawler", x=50, y=-20, index=4),
        ],
    )
    threat = ThreatSignal(
        key="enemy_chaff_overload", severity=0.7, urgency=ThreatUrgency.MEDIUM,
        source_units=["crawler"], my_answer=AnswerStrength.WEAK,
    )
    feats = _features(threats=[threat])
    summary = _build_and_analyze(state, feats)
    chaff_findings = [f for f in summary.tactical_findings if f.key == "anti_chaff_gap"]
    assert len(chaff_findings) > 0


# ── Anti-heavy gap ───────────────────────────────────────────────────────────


def test_anti_heavy_gap_on_frontline_wall():
    state = _state(
        my_units=[_unit("crawler", x=0, y=-100)],
        enemy_units=[
            _unit("fortress", x=0, y=-30, index=0),
            _unit("rhino", x=-100, y=-30, index=1),
        ],
    )
    threat = ThreatSignal(
        key="enemy_frontline_wall", severity=0.8, urgency=ThreatUrgency.HIGH,
        source_units=["fortress", "rhino"], my_answer=AnswerStrength.NONE,
    )
    feats = _features(threats=[threat])
    summary = _build_and_analyze(state, feats)
    heavy_findings = [f for f in summary.tactical_findings if f.key == "anti_heavy_gap"]
    assert len(heavy_findings) > 0


# ── Artillery danger ─────────────────────────────────────────────────────────


def test_artillery_danger_on_backline():
    state = _state(
        my_units=[_unit("marksmen", x=0, y=-250)],
        enemy_units=[_unit("sledgehammer", x=0, y=-50, level=2)],
    )
    feats = _features()
    summary = _build_and_analyze(state, feats)
    art_findings = [f for f in summary.tactical_findings if f.key == "artillery_danger"]
    assert len(art_findings) > 0


# ── Flank opportunity ────────────────────────────────────────────────────────


def test_flank_opportunity_when_flank_weak():
    state = _state(
        my_units=[
            _unit("marksmen", x=-200, y=-150, index=0),
            _unit("marksmen", x=-100, y=-150, index=1),
        ],
        enemy_units=[_unit("fortress", x=100, y=80)],
    )
    feats = _features()
    summary = _build_and_analyze(state, feats)
    flank_findings = [f for f in summary.tactical_findings if f.key == "flank_opportunity"]
    if flank_findings:
        assert any(f.zone in (MapZone.LEFT_FRONT, MapZone.LEFT_MID, MapZone.LEFT_BACK) for f in flank_findings)


# ── Tower pressure ───────────────────────────────────────────────────────────


def test_tower_pressure_detected():
    tower = ConstructionView(
        type=ConstructionType.COMMAND_TOWER,
        role=ConstructionRole.COMMAND,
        position=Position(x=0, y=-150),
        position_label="center_mid",
    )
    state = _state(
        my_units=[_unit("crawler", x=0, y=-200)],
        enemy_units=[
            _unit("sledgehammer", x=0, y=-80, level=2, index=0),
            _unit("marksmen", x=50, y=-80, level=2, index=1),
        ],
        constructions=[tower],
    )
    feats = _features()
    summary = _build_and_analyze(state, feats)
    tower_findings = [f for f in summary.tactical_findings if f.key == "tower_pressure"]
    assert len(tower_findings) > 0


def test_no_tower_pressure_without_constructions():
    state = _state(
        my_units=[_unit("crawler", x=0, y=-100)],
        enemy_units=[_unit("sledgehammer", x=0, y=80)],
    )
    feats = _features()
    summary = _build_and_analyze(state, feats)
    tower_findings = [f for f in summary.tactical_findings if f.key == "tower_pressure"]
    assert len(tower_findings) == 0


# ── Golden: anti-air response reduces gap ─────────────────────────────────────


def test_adding_anti_air_reduces_gap():
    threat = ThreatSignal(
        key="enemy_air_pressure", severity=0.9, urgency=ThreatUrgency.HIGH,
        source_units=["wasp"], my_answer=AnswerStrength.NONE,
    )
    enemy = [
        _unit("wasp", x=0, y=-30, level=2, index=0),
        _unit("wasp", x=100, y=-30, level=2, index=1),
    ]
    without_aa = _state(
        my_units=[_unit("crawler", x=0, y=-150)],
        enemy_units=enemy,
    )
    with_aa = _state(
        my_units=[_unit("crawler", x=0, y=-150), _unit("mustang", x=50, y=-150, index=1)],
        enemy_units=enemy,
    )
    feats = _features(threats=[threat])

    summary_without = _build_and_analyze(without_aa, feats)
    summary_with = _build_and_analyze(with_aa, feats)

    gaps_without = [f for f in summary_without.tactical_findings if f.key == "anti_air_gap"]
    gaps_with = [f for f in summary_with.tactical_findings if f.key == "anti_air_gap"]

    max_sev_without = max((f.severity for f in gaps_without), default=0)
    max_sev_with = max((f.severity for f in gaps_with), default=0)
    assert max_sev_with < max_sev_without or len(gaps_with) < len(gaps_without)


# ── Findings sorted by severity ──────────────────────────────────────────────


def test_findings_sorted_by_severity():
    state = _state(
        my_units=[_unit("crawler", x=0, y=-150)],
        enemy_units=[
            _unit("wasp", x=0, y=-30, level=2, index=0),
            _unit("wasp", x=100, y=-30, level=2, index=1),
            _unit("fortress", x=-100, y=-30, index=2),
        ],
    )
    threat_air = ThreatSignal(
        key="enemy_air_pressure", severity=0.9, urgency=ThreatUrgency.HIGH,
        source_units=["wasp"], my_answer=AnswerStrength.NONE,
    )
    threat_heavy = ThreatSignal(
        key="enemy_frontline_wall", severity=0.6, urgency=ThreatUrgency.MEDIUM,
        source_units=["fortress"], my_answer=AnswerStrength.WEAK,
    )
    feats = _features(threats=[threat_air, threat_heavy])
    summary = _build_and_analyze(state, feats)

    if len(summary.tactical_findings) >= 2:
        severities = [f.severity for f in summary.tactical_findings]
        assert severities == sorted(severities, reverse=True)


# ── Empty/low-threat state ───────────────────────────────────────────────────


def test_no_false_high_severity_on_empty_state():
    state = _state()
    feats = _features()
    summary = _build_and_analyze(state, feats)
    for f in summary.tactical_findings:
        assert f.severity < 0.5, f"Unexpected high severity: {f.key} = {f.severity}"


def test_low_threat_state_produces_few_findings():
    state = _state(
        my_units=[_unit("crawler", x=0, y=-150)],
        enemy_units=[_unit("crawler", x=0, y=150)],
    )
    feats = _features()
    summary = _build_and_analyze(state, feats)
    high_sev = [f for f in summary.tactical_findings if f.severity > 0.5]
    assert len(high_sev) == 0


# ── Global assessment ────────────────────────────────────────────────────────


def test_global_assessment_present():
    state = _state(
        my_units=[_unit("marksmen", x=0, y=-150)],
        enemy_units=[_unit("wasp", x=0, y=100)],
    )
    feats = _features()
    summary = _build_and_analyze(state, feats)
    assert "ground_balance" in summary.global_assessment
    assert "air_balance" in summary.global_assessment
    assert "frontline_balance" in summary.global_assessment
    assert "artillery_pressure" in summary.global_assessment


# ── Critical zones ───────────────────────────────────────────────────────────


def test_critical_zones_subset_of_zones():
    state = _state(
        my_units=[_unit("crawler", x=0, y=-150)],
        enemy_units=[_unit("fortress", x=0, y=80, level=3)],
    )
    feats = _features()
    summary = _build_and_analyze(state, feats)
    zone_ids = {z.zone for z in summary.zones}
    for cz in summary.critical_zones:
        assert cz.zone in zone_ids


# ── Summary is InfluenceAnalysisSummary ──────────────────────────────────────


def test_returns_influence_analysis_summary():
    state = _state(my_units=[_unit("crawler", x=0, y=-150)])
    feats = _features()
    summary = _build_and_analyze(state, feats)
    assert isinstance(summary, InfluenceAnalysisSummary)
    assert len(summary.zones) == 9


# ── JSON serializable ────────────────────────────────────────────────────────


def test_summary_json_serializable():
    import json
    state = _state(
        my_units=[_unit("marksmen", x=0, y=-150)],
        enemy_units=[_unit("wasp", x=0, y=100)],
    )
    threat = ThreatSignal(
        key="enemy_air_pressure", severity=0.9, urgency=ThreatUrgency.HIGH,
        source_units=["wasp"], my_answer=AnswerStrength.NONE,
    )
    feats = _features(threats=[threat])
    summary = _build_and_analyze(state, feats)
    data = summary.model_dump(mode="json")
    s = json.dumps(data)
    assert isinstance(s, str)
    loaded = json.loads(s)
    assert loaded["version"] == "v1"
