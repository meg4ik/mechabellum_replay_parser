"""Tests for FeatureExtractor."""

import pytest

from mechabellum_replay_parser.coach.feature_extractor import (
    FeatureExtractor,
)
from mechabellum_replay_parser.coach.schemas import (
    ArmyProfile,
    AnswerStrength,
    ConstructionType,
    ConstructionView,
    PlayerRoundView,
    Position,
    ShopView,
    StateView,
    StrategicMemory,
    TacticalFeatures,
    ThreatUrgency,
    UnitView,
)


def _make_unit(name: str, x: int = 0, y: int = -100) -> UnitView:
    return UnitView(name=name, position=Position(x=x, y=y))


def _make_state(
    my_units: list[UnitView],
    enemy_units: list[UnitView],
    my_av: int = 500,
    enemy_av: int = 500,
    my_constructions: list[ConstructionView] | None = None,
    strategic_memory: StrategicMemory | None = None,
) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=3,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=200,
        my_state=PlayerRoundView(
            name="Me",
            army_value=my_av,
            units=my_units,
            constructions=my_constructions or [],
            shop=ShopView(buys_remaining=4, unlocks_remaining=1),
        ),
        enemy_states=[
            PlayerRoundView(
                name="Enemy",
                army_value=enemy_av,
                units=enemy_units,
            )
        ],
        recent_rounds=[],
        strategic_memory=strategic_memory or StrategicMemory(),
    )


@pytest.fixture
def extractor():
    return FeatureExtractor()


# ── No threats ────────────────────────────────────────────────────────────────


def test_no_threats_empty_enemy(extractor):
    state = _make_state([], [])
    features = extractor.extract(state)
    assert features.threats == []


def test_no_air_threat_without_enemy_air(extractor):
    state = _make_state([], [_make_unit("crawler")])
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_air_pressure" not in keys


# ── Air pressure ──────────────────────────────────────────────────────────────


def test_air_threat_detected(extractor):
    state = _make_state([], [_make_unit("phoenix")])
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_air_pressure" in keys


def test_air_threat_severity_no_aa(extractor):
    state = _make_state([], [_make_unit("phoenix")])
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert air.severity >= 0.8
    assert air.my_answer == "none"


def test_air_threat_weak_with_one_aa(extractor):
    state = _make_state([_make_unit("arclight")], [_make_unit("phoenix")])
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert air.my_answer == "weak"
    assert air.severity < 0.8


def test_air_threat_good_with_two_aa(extractor):
    state = _make_state(
        [_make_unit("arclight"), _make_unit("mustang")],
        [_make_unit("phoenix")],
    )
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert air.my_answer == "strong"
    assert air.severity < 0.5


def test_air_threat_source_units(extractor):
    state = _make_state([], [_make_unit("wasp"), _make_unit("phoenix")])
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert "phoenix" in air.source_units
    assert "wasp" in air.source_units


def test_no_aa_adds_to_weaknesses(extractor):
    state = _make_state([], [_make_unit("overlord")])
    features = extractor.extract(state)
    assert any("anti-air" in w for w in features.my_weaknesses)


# ── Chaff overload ────────────────────────────────────────────────────────────


def test_chaff_threat_below_threshold(extractor):
    state = _make_state([], [_make_unit("crawler")] * 3)
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_chaff_overload" not in keys


def test_chaff_threat_at_threshold(extractor):
    state = _make_state([], [_make_unit("crawler")] * 4)
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_chaff_overload" in keys


def test_chaff_threat_no_splash_my_answer_none(extractor):
    state = _make_state([_make_unit("fortress")], [_make_unit("fang")] * 4)
    features = extractor.extract(state)
    chaff = next(t for t in features.threats if t.key == "enemy_chaff_overload")
    assert chaff.my_answer == "none"
    assert chaff.severity >= 0.6


def test_chaff_threat_with_splash_my_answer_good(extractor):
    state = _make_state(
        [_make_unit("arclight")],
        [_make_unit("crawler")] * 4,
    )
    features = extractor.extract(state)
    chaff = next(t for t in features.threats if t.key == "enemy_chaff_overload")
    assert chaff.my_answer == "strong"


# ── Artillery pressure ────────────────────────────────────────────────────────


def test_artillery_threat_detected(extractor):
    state = _make_state([], [_make_unit("stormcaller")])
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_artillery_pressure" in keys


def test_no_artillery_threat_without_artillery(extractor):
    state = _make_state([], [_make_unit("rhino")])
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_artillery_pressure" not in keys


# ── Heavy frontline ───────────────────────────────────────────────────────────


def test_no_heavy_threat_single_heavy(extractor):
    state = _make_state([], [_make_unit("fortress")])
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_frontline_wall" not in keys


def test_heavy_threat_two_heavies(extractor):
    state = _make_state([], [_make_unit("fortress"), _make_unit("rhino")])
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_frontline_wall" in keys


# ── Tempo state ───────────────────────────────────────────────────────────────


def test_tempo_even(extractor):
    state = _make_state([], [], my_av=500, enemy_av=500)
    features = extractor.extract(state)
    assert features.tempo_state == "even"


def test_tempo_ahead(extractor):
    state = _make_state([], [], my_av=700, enemy_av=500)
    features = extractor.extract(state)
    assert features.tempo_state == "ahead"


def test_tempo_behind(extractor):
    state = _make_state([], [], my_av=300, enemy_av=500)
    features = extractor.extract(state)
    assert features.tempo_state == "behind"


def test_tempo_unknown_both_zero(extractor):
    state = _make_state([], [], my_av=0, enemy_av=0)
    features = extractor.extract(state)
    assert features.tempo_state == "unknown"


# ── Board posture ─────────────────────────────────────────────────────────────


def test_board_posture_unknown_no_units(extractor):
    state = _make_state([], [])
    features = extractor.extract(state)
    assert features.board_posture == "unknown"


def test_board_posture_aggro_front_line(extractor):
    state = _make_state([_make_unit("rhino", x=0, y=-60)], [])
    features = extractor.extract(state)
    assert features.board_posture == "aggro"


def test_board_posture_standard(extractor):
    state = _make_state([_make_unit("rhino", x=0, y=-150)], [])
    features = extractor.extract(state)
    assert features.board_posture == "standard"


def test_board_posture_defensive_back_line(extractor):
    state = _make_state([_make_unit("stormcaller", x=0, y=-280)], [])
    features = extractor.extract(state)
    assert features.board_posture == "defensive"


# ── Tower notes ───────────────────────────────────────────────────────────────


def test_tower_notes_no_constructions(extractor):
    state = _make_state([], [])
    features = extractor.extract(state)
    assert any("No constructions" in n for n in features.tower_notes)


def test_tower_notes_with_construction(extractor):
    state = _make_state(
        [],
        [],
        my_constructions=[
            ConstructionView(
                type=ConstructionType.SUPPLY_TOWER, position=Position(x=100, y=-270)
            )
        ],
    )
    features = extractor.extract(state)
    assert any("supply_tower" in n for n in features.tower_notes)


# ── Priority questions ────────────────────────────────────────────────────────


def test_priority_question_when_behind(extractor):
    state = _make_state([], [], my_av=200, enemy_av=500)
    features = extractor.extract(state)
    assert any("recover" in q.lower() for q in features.priority_questions)


def test_priority_question_when_ahead(extractor):
    state = _make_state([], [], my_av=700, enemy_av=500)
    features = extractor.extract(state)
    assert any("advantage" in q.lower() for q in features.priority_questions)


# ── Strategic memory flows through ────────────────────────────────────────────


def test_do_not_forget_in_likely_continuation(extractor):
    mem = StrategicMemory(
        do_not_forget=["Enemy has been investing in phoenix for 2 round(s)."]
    )
    state = _make_state([], [], strategic_memory=mem)
    features = extractor.extract(state)
    assert (
        "Enemy has been investing in phoenix for 2 round(s)."
        in features.likely_enemy_continuation
    )


# ── Full pipeline with parsed_replay fixture ──────────────────────────────────


def test_extract_from_parsed_replay(parsed_replay):
    from mechabellum_replay_parser.coach.state_view import StateViewBuilder

    builder = StateViewBuilder()
    extractor = FeatureExtractor()
    state = builder.build(parsed_replay, supply=100, player_name="Player1")
    features = extractor.extract(state)

    assert isinstance(features, TacticalFeatures)
    # Player2 has no units → no air/chaff/heavy threats from enemy
    assert features.threats == []
    # Player1 has 1 crawler at y=-80 → aggro
    assert features.board_posture == "aggro"
    assert isinstance(features.my_army_profile, ArmyProfile)
    assert isinstance(features.enemy_army_profile, ArmyProfile)


# ── ThreatSignal urgency ──────────────────────────────────────────────────────


def test_air_threat_urgency_critical_no_aa(extractor):
    state = _make_state([], [_make_unit("phoenix")])
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert air.urgency == ThreatUrgency.CRITICAL


def test_air_threat_urgency_high_weak_aa(extractor):
    state = _make_state([_make_unit("arclight")], [_make_unit("phoenix")])
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert air.urgency == ThreatUrgency.HIGH


def test_air_threat_urgency_low_strong_aa(extractor):
    state = _make_state(
        [_make_unit("arclight"), _make_unit("mustang")], [_make_unit("phoenix")]
    )
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert air.urgency == ThreatUrgency.LOW


def test_threat_has_recommended_response_types(extractor):
    state = _make_state([], [_make_unit("phoenix")])
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert len(air.recommended_response_types) > 0
    assert len(air.bad_response_types) > 0


def test_answer_strength_enum_equality(extractor):
    state = _make_state([], [_make_unit("phoenix")])
    features = extractor.extract(state)
    air = next(t for t in features.threats if t.key == "enemy_air_pressure")
    assert air.my_answer == AnswerStrength.NONE
    assert air.my_answer == "none"  # str-enum equality


# ── ArmyProfile ───────────────────────────────────────────────────────────────


def test_army_profile_empty_units(extractor):
    state = _make_state([], [])
    features = extractor.extract(state)
    assert features.my_army_profile.chaff == 0.0
    assert features.my_army_profile.anti_air == 0.0


def test_army_profile_chaff_with_crawlers(extractor):
    state = _make_state([_make_unit("crawler"), _make_unit("fang")], [])
    features = extractor.extract(state)
    assert features.my_army_profile.chaff > 0.0


def test_army_profile_anti_air_with_arclight(extractor):
    state = _make_state([_make_unit("arclight")], [])
    features = extractor.extract(state)
    assert features.my_army_profile.anti_air > 0.0


def test_enemy_profile_air_pressure_with_phoenix(extractor):
    state = _make_state([], [_make_unit("phoenix")])
    features = extractor.extract(state)
    assert features.enemy_army_profile.air_pressure > 0.0


def test_army_profile_scaling_with_warfactory(extractor):
    state = _make_state([_make_unit("warfactory")], [])
    features = extractor.extract(state)
    assert features.my_army_profile.scaling > 0.0


# ── New feature keys ──────────────────────────────────────────────────────────


def test_enemy_scaling_threat_detected(extractor):
    state = _make_state([], [_make_unit("warfactory"), _make_unit("warfactory")])
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "enemy_has_scaling_carry" in keys


def test_enemy_lacks_anti_heavy_adds_weakness(extractor):
    state = _make_state(
        [_make_unit("fortress"), _make_unit("rhino")],
        [_make_unit("fang")],
    )
    features = extractor.extract(state)
    assert any("anti-heavy" in w for w in features.enemy_weaknesses)


def test_positioning_clump_risk_detected(extractor):
    state = _make_state(
        [
            _make_unit("crawler", x=10, y=-100),
            _make_unit("fang", x=20, y=-120),
            _make_unit("hound", x=30, y=-110),
        ],
        [],
    )
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "positioning_clump_risk" in keys


def test_positioning_clump_risk_not_detected_when_spread(extractor):
    state = _make_state(
        [
            _make_unit("crawler", x=-200, y=-100),
            _make_unit("fang", x=0, y=-150),
            _make_unit("hound", x=200, y=-200),
        ],
        [],
    )
    features = extractor.extract(state)
    keys = {t.key for t in features.threats}
    assert "positioning_clump_risk" not in keys
