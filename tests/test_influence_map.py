from __future__ import annotations

import numpy as np

from mechabellum_replay_parser.coach.coordinates import CoordinateFrame
from mechabellum_replay_parser.coach.influence_map import (
    InfluenceMapBuilder,
    InfluenceMapResult,
)
from mechabellum_replay_parser.coach.influence_schemas import MapZone
from mechabellum_replay_parser.coach.schemas import (
    PlayerRoundView,
    PlayerSide,
    Position,
    ShopView,
    StateView,
    StrategicMemory,
    UnitView,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _unit(
    name: str,
    x: int = 0,
    y: int = -100,
    level: int = 1,
    index: int = 0,
    techs: list[str] | None = None,
) -> UnitView:
    return UnitView(
        name=name, unit_id=0, index=index, level=level, exp=0,
        position=Position(x=x, y=y),
        active_techs=techs or [],
    )


def _state(
    my_units: list[UnitView] | None = None,
    enemy_units: list[UnitView] | None = None,
) -> StateView:
    return StateView(
        match_mode="VS_1_1",
        round=3,
        player_name="Me",
        enemy_names=["Enemy"],
        my_supply=600,
        my_state=PlayerRoundView(
            name="Me",
            units=my_units or [],
            shop=ShopView(buys_remaining=3, unlocks_remaining=1),
        ),
        enemy_states=[
            PlayerRoundView(name="Enemy", units=enemy_units or []),
        ],
        recent_rounds=[],
        strategic_memory=StrategicMemory(),
    )


def _neg_frame() -> CoordinateFrame:
    return CoordinateFrame.for_side(PlayerSide.NEGATIVE_Y)


def _pos_frame() -> CoordinateFrame:
    return CoordinateFrame.for_side(PlayerSide.POSITIVE_Y)


# ── Empty board ──────────────────────────────────────────────────────────────


def test_empty_board_returns_zero_fields():
    builder = InfluenceMapBuilder()
    result = builder.build(_state(), _neg_frame())
    assert isinstance(result, InfluenceMapResult)
    assert np.all(result.arrays.my_ground == 0)
    assert np.all(result.arrays.enemy_ground == 0)
    assert np.all(result.arrays.my_air == 0)
    assert np.all(result.arrays.enemy_durability == 0)


def test_empty_board_zones_all_zero():
    builder = InfluenceMapBuilder()
    result = builder.build(_state(), _neg_frame())
    assert len(result.zones) == 9
    for z in result.zones:
        assert z.my_ground == 0.0
        assert z.enemy_ground == 0.0


# ── Single unit range influence ──────────────────────────────────────────────


def test_single_unit_center_has_higher_influence_near_center():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("marksmen", x=0, y=-150)])
    result = builder.build(state, _neg_frame())

    h, w = result.arrays.my_ground.shape
    center_val = result.arrays.my_ground[h // 2, w // 2]
    edge_val = result.arrays.my_ground[h // 2, 0]
    assert center_val > edge_val


def test_unit_range_affects_coverage():
    builder = InfluenceMapBuilder()
    short_range = _state(my_units=[_unit("crawler", x=0, y=-150)])
    long_range = _state(my_units=[_unit("marksmen", x=0, y=-150)])
    res_short = builder.build(short_range, _neg_frame())
    res_long = builder.build(long_range, _neg_frame())

    far_row = 0
    far_col = res_short.arrays.my_ground.shape[1] // 2
    assert res_long.arrays.my_ground[far_row, far_col] > res_short.arrays.my_ground[far_row, far_col]


# ── Level scaling ────────────────────────────────────────────────────────────


def test_level2_influence_greater_than_level1():
    builder = InfluenceMapBuilder()
    lv1 = _state(my_units=[_unit("crawler", level=1, x=0, y=-150)])
    lv2 = _state(my_units=[_unit("crawler", level=2, x=0, y=-150)])
    res1 = builder.build(lv1, _neg_frame())
    res2 = builder.build(lv2, _neg_frame())
    assert res2.arrays.my_ground.sum() > res1.arrays.my_ground.sum()


# ── Tech impact ──────────────────────────────────────────────────────────────


def test_range_tech_increases_coverage():
    builder = InfluenceMapBuilder()
    without = _state(my_units=[_unit("marksmen", x=0, y=-200)])
    with_tech = _state(my_units=[_unit("marksmen", x=0, y=-200, techs=["Range enhancement"])])
    res_without = builder.build(without, _neg_frame())
    res_with = builder.build(with_tech, _neg_frame())
    assert res_with.arrays.my_ground.sum() > res_without.arrays.my_ground.sum()


# ── Air channels ─────────────────────────────────────────────────────────────


def test_air_unit_writes_air_channel():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("mustang", x=0, y=-150)])
    result = builder.build(state, _neg_frame())
    assert result.arrays.my_air.sum() > 0


def test_ground_only_unit_no_air_influence():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("crawler", x=0, y=-150)])
    result = builder.build(state, _neg_frame())
    assert result.arrays.my_air.sum() == 0


# ── Anti-chaff / anti-heavy ──────────────────────────────────────────────────


def test_anti_chaff_unit_has_chaff_influence():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("vulcan", x=0, y=-150)])
    result = builder.build(state, _neg_frame())
    assert result.arrays.my_anti_chaff.sum() > 0


def test_anti_heavy_unit_has_heavy_influence():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("marksmen", x=0, y=-150)])
    result = builder.build(state, _neg_frame())
    assert result.arrays.my_anti_heavy.sum() > 0


# ── Artillery channel ────────────────────────────────────────────────────────


def test_artillery_unit_writes_artillery_channel():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("stormcaller", x=0, y=-200)])
    result = builder.build(state, _neg_frame())
    assert result.arrays.my_artillery.sum() > 0


def test_non_artillery_unit_no_artillery():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("crawler", x=0, y=-150)])
    result = builder.build(state, _neg_frame())
    assert result.arrays.my_artillery.sum() == 0


# ── Durability channel ──────────────────────────────────────────────────────


def test_durability_proportional_to_hp():
    builder = InfluenceMapBuilder()
    light = _state(my_units=[_unit("crawler", x=0, y=-150)])
    heavy = _state(my_units=[_unit("fortress", x=0, y=-150)])
    res_light = builder.build(light, _neg_frame())
    res_heavy = builder.build(heavy, _neg_frame())
    assert res_heavy.arrays.my_durability.sum() > res_light.arrays.my_durability.sum()


# ── Enemy units ──────────────────────────────────────────────────────────────


def test_enemy_units_write_to_enemy_channels():
    builder = InfluenceMapBuilder()
    state = _state(enemy_units=[_unit("crawler", x=0, y=150)])
    result = builder.build(state, _neg_frame())
    assert result.arrays.enemy_ground.sum() > 0
    assert result.arrays.my_ground.sum() == 0


# ── Positive-Y side ─────────────────────────────────────────────────────────


def test_positive_y_side_works():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("crawler", x=0, y=150, level=1)])
    result = builder.build(state, _pos_frame())
    assert result.arrays.my_ground.sum() > 0
    assert result.grid.player_side == "positive_y"


# ── Zone aggregation ─────────────────────────────────────────────────────────


def test_zones_count():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("marksmen", x=0, y=-150)])
    result = builder.build(state, _neg_frame())
    assert len(result.zones) == 9


def test_zone_values_bounded():
    builder = InfluenceMapBuilder()
    state = _state(
        my_units=[_unit("marksmen", x=0, y=-150)],
        enemy_units=[_unit("wasp", x=100, y=100)],
    )
    result = builder.build(state, _neg_frame())
    for z in result.zones:
        for field_name in (
            "my_ground", "enemy_ground", "my_air", "enemy_air",
            "my_anti_chaff", "enemy_anti_chaff", "my_anti_heavy", "enemy_anti_heavy",
            "danger_for_my_ground", "danger_for_my_air", "opportunity_score",
        ):
            val = getattr(z, field_name)
            assert 0.0 <= val <= 1.0, f"{z.zone}.{field_name} = {val}"


def test_all_nine_zones_present():
    builder = InfluenceMapBuilder()
    state = _state(my_units=[_unit("marksmen", x=0, y=-150)])
    result = builder.build(state, _neg_frame())
    zone_ids = {z.zone for z in result.zones}
    assert zone_ids == set(MapZone)


# ── No NaN / Inf ─────────────────────────────────────────────────────────────


def test_no_nan_or_inf():
    builder = InfluenceMapBuilder()
    state = _state(
        my_units=[_unit("marksmen", x=-200, y=-80), _unit("crawler", x=100, y=-200)],
        enemy_units=[_unit("wasp", x=0, y=100), _unit("fortress", x=-50, y=80)],
    )
    result = builder.build(state, _neg_frame())
    for name in (
        "my_ground", "enemy_ground", "my_air", "enemy_air",
        "my_anti_chaff", "enemy_anti_chaff", "my_anti_heavy", "enemy_anti_heavy",
        "my_artillery", "enemy_artillery", "my_durability", "enemy_durability",
    ):
        arr = getattr(result.arrays, name)
        assert not np.any(np.isnan(arr)), f"NaN in {name}"
        assert not np.any(np.isinf(arr)), f"Inf in {name}"


# ── Deterministic ────────────────────────────────────────────────────────────


def test_deterministic():
    builder = InfluenceMapBuilder()
    state = _state(
        my_units=[_unit("marksmen", x=0, y=-150)],
        enemy_units=[_unit("wasp", x=50, y=100)],
    )
    frame = _neg_frame()
    res1 = builder.build(state, frame)
    res2 = builder.build(state, frame)
    np.testing.assert_array_equal(res1.arrays.my_ground, res2.arrays.my_ground)
    np.testing.assert_array_equal(res1.arrays.enemy_ground, res2.arrays.enemy_ground)


# ── Grid spec ────────────────────────────────────────────────────────────────


def test_grid_spec_matches_frame():
    builder = InfluenceMapBuilder(grid_width=15, grid_height=10)
    state = _state(my_units=[_unit("crawler", x=0, y=-150)])
    result = builder.build(state, _neg_frame())
    assert result.grid.width == 15
    assert result.grid.height == 10
    assert result.arrays.my_ground.shape == (10, 15)


# ── Performance ──────────────────────────────────────────────────────────────


def test_build_performance_under_50ms():
    import time
    builder = InfluenceMapBuilder()
    my_units = [_unit("marksmen", x=-200 + i * 50, y=-150, index=i) for i in range(6)]
    enemy_units = [_unit("crawler", x=-150 + i * 60, y=-30, index=i) for i in range(8)]
    state = _state(my_units=my_units, enemy_units=enemy_units)
    frame = _neg_frame()

    t0 = time.perf_counter()
    for _ in range(5):
        builder.build(state, frame)
    elapsed = (time.perf_counter() - t0) / 5 * 1000

    assert elapsed < 200, f"InfluenceMapBuilder.build() took {elapsed:.1f}ms (target <50ms, allowing 4x margin)"


def test_analyzer_performance_under_20ms():
    import time
    from mechabellum_replay_parser.coach.influence_analyzer import InfluenceAnalyzer
    from mechabellum_replay_parser.coach.schemas import (
        ArmyProfile,
        TacticalFeatures,
        ThreatSignal,
        ThreatUrgency,
        AnswerStrength,
    )

    builder = InfluenceMapBuilder()
    analyzer = InfluenceAnalyzer()
    my_units = [_unit("marksmen", x=-100, y=-150, index=0), _unit("arclight", x=50, y=-150, index=1)]
    enemy_units = [_unit("wasp", x=0, y=-30, level=2, index=0), _unit("fortress", x=-50, y=-30, index=1)]
    state = _state(my_units=my_units, enemy_units=enemy_units)
    features = TacticalFeatures(
        threats=[ThreatSignal(key="enemy_air_pressure", severity=0.9, urgency=ThreatUrgency.HIGH,
                              source_units=["wasp"], my_answer=AnswerStrength.NONE)],
        my_weaknesses=[], enemy_weaknesses=[],
        tempo_state="even", board_posture="standard",
        tower_notes=[], likely_enemy_continuation=[], priority_questions=[],
        my_army_profile=ArmyProfile(), enemy_army_profile=ArmyProfile(),
    )
    frame = _neg_frame()
    influence = builder.build(state, frame)

    t0 = time.perf_counter()
    for _ in range(10):
        analyzer.analyze(state, features, influence)
    elapsed = (time.perf_counter() - t0) / 10 * 1000

    assert elapsed < 100, f"InfluenceAnalyzer.analyze() took {elapsed:.1f}ms (target <20ms, allowing 5x margin)"
