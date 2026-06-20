from __future__ import annotations

import json

from mechabellum_replay_parser.coach.schemas import UnitView
from mechabellum_replay_parser.coach.unit_stats import (
    ResolvedUnitStats,
    UnitStatsResolver,
    get_combat_stats,
)


def _unit(name: str, level: int = 1, index: int = 0, techs: list[str] | None = None) -> UnitView:
    return UnitView(
        name=name,
        unit_id=0,
        index=index,
        level=level,
        exp=0,
        active_techs=techs or [],
    )


# ── Base stats loading ──────────────────────────────────────────────────────


def test_base_stats_load_known_unit():
    stats = get_combat_stats("crawler")
    assert stats.unit == "crawler"
    assert stats.base_hp > 0
    assert stats.base_dps_ground > 0
    assert stats.squad_size > 1


def test_base_stats_load_marksmen():
    stats = get_combat_stats("marksmen")
    assert stats.target_profile.can_hit_air is True
    assert stats.target_profile.prefers_heavy is True
    assert stats.range > 50


def test_base_stats_case_insensitive():
    stats = get_combat_stats("Crawler")
    assert stats.unit == "crawler"
    assert stats.base_hp > 0


# ── Unknown unit fallback ───────────────────────────────────────────────────


def test_unknown_unit_returns_fallback():
    stats = get_combat_stats("nonexistent_unit_xyz")
    assert stats.unit == "nonexistent_unit_xyz"
    assert stats.base_hp > 0
    assert stats.base_dps_ground > 0
    assert stats.range > 0


def test_unknown_unit_resolver_no_crash():
    resolver = UnitStatsResolver()
    result = resolver.resolve_unit(_unit("nonexistent_unit_xyz", level=3))
    assert isinstance(result, ResolvedUnitStats)
    assert result.unit == "nonexistent_unit_xyz"
    assert result.level == 3


# ── Level scaling ───────────────────────────────────────────────────────────


def test_level_scaling_level2_greater_than_level1():
    resolver = UnitStatsResolver()
    lv1 = resolver.resolve_unit(_unit("crawler", level=1))
    lv2 = resolver.resolve_unit(_unit("crawler", level=2))
    assert lv2.effective_hp > lv1.effective_hp
    assert lv2.effective_dps_ground > lv1.effective_dps_ground


def test_level_scaling_formula():
    resolver = UnitStatsResolver()
    base = get_combat_stats("crawler")
    lv3 = resolver.resolve_unit(_unit("crawler", level=3))
    expected_mult = 1.0 + 0.35 * 2
    assert abs(lv3.effective_hp - base.base_hp * expected_mult) < 1.0


def test_level1_no_scaling():
    resolver = UnitStatsResolver()
    base = get_combat_stats("crawler")
    lv1 = resolver.resolve_unit(_unit("crawler", level=1))
    assert abs(lv1.effective_hp - base.base_hp) < 1.0


# ── Tech modifiers ──────────────────────────────────────────────────────────


def test_range_tech_increases_range():
    resolver = UnitStatsResolver()
    without = resolver.resolve_unit(_unit("marksmen", level=1))
    with_tech = resolver.resolve_unit(_unit("marksmen", level=1, techs=["Range enhancement"]))
    assert with_tech.effective_range > without.effective_range
    assert "Range enhancement" in with_tech.applied_modifiers


def test_damage_tech_increases_dps():
    resolver = UnitStatsResolver()
    without = resolver.resolve_unit(_unit("arclight", level=1))
    with_tech = resolver.resolve_unit(_unit("arclight", level=1, techs=["Damage enhancement"]))
    assert with_tech.effective_dps_ground > without.effective_dps_ground
    assert with_tech.effective_dps_air > without.effective_dps_air


def test_hp_tech_increases_hp():
    resolver = UnitStatsResolver()
    without = resolver.resolve_unit(_unit("fortress", level=1))
    with_tech = resolver.resolve_unit(_unit("fortress", level=1, techs=["Armor enhancement"]))
    assert with_tech.effective_hp > without.effective_hp


def test_tech_via_active_techs_dict():
    resolver = UnitStatsResolver()
    unit = _unit("marksmen", level=1)
    techs = [{"unit": "marksmen", "tech": "Range enhancement"}]
    result = resolver.resolve_unit(unit, active_techs=techs)
    assert result.effective_range > get_combat_stats("marksmen").range


def test_tech_only_applies_to_matching_unit():
    resolver = UnitStatsResolver()
    unit = _unit("crawler", level=1)
    techs = [{"unit": "marksmen", "tech": "Range enhancement"}]
    without = resolver.resolve_unit(_unit("crawler", level=1))
    with_wrong_tech = resolver.resolve_unit(unit, active_techs=techs)
    assert with_wrong_tech.effective_range == without.effective_range


def test_unknown_tech_ignored():
    resolver = UnitStatsResolver()
    result = resolver.resolve_unit(_unit("crawler", level=1, techs=["Imaginary Tech"]))
    base = get_combat_stats("crawler")
    assert abs(result.effective_hp - base.base_hp) < 1.0


# ── Fixture unit resolution ─────────────────────────────────────────────────


def test_air_threat_fixture_units_all_resolve():
    resolver = UnitStatsResolver()
    fixture_units = ["crawler", "wasp"]
    for name in fixture_units:
        result = resolver.resolve_unit(_unit(name, level=2))
        assert result.unit == name
        assert result.effective_hp > 0
        assert result.level == 2


def test_all_combat_data_units_resolve():
    resolver = UnitStatsResolver()
    from mechabellum_replay_parser.coach.unit_stats import _load_combat_data

    all_units = _load_combat_data()
    for name in all_units:
        result = resolver.resolve_unit(_unit(name, level=1))
        assert result.unit == name
        assert result.effective_hp > 0


# ── JSON serialization ──────────────────────────────────────────────────────


def test_resolved_stats_json_serializable():
    resolver = UnitStatsResolver()
    result = resolver.resolve_unit(_unit("marksmen", level=2, techs=["Range enhancement"]))
    data = result.model_dump(mode="json")
    serialized = json.dumps(data)
    assert isinstance(serialized, str)
    loaded = json.loads(serialized)
    assert loaded["unit"] == "marksmen"
    assert loaded["level"] == 2


def test_combat_stats_json_serializable():
    stats = get_combat_stats("crawler")
    data = stats.model_dump(mode="json")
    serialized = json.dumps(data)
    assert isinstance(serialized, str)


# ── resolve_many ────────────────────────────────────────────────────────────


def test_resolve_many_returns_dict():
    resolver = UnitStatsResolver()
    units = [
        _unit("crawler", level=1, index=0),
        _unit("crawler", level=2, index=1),
        _unit("wasp", level=1, index=0),
    ]
    result = resolver.resolve_many(units)
    assert isinstance(result, dict)
    assert len(result) == 3
    assert "crawler_0" in result
    assert "crawler_1" in result
    assert "wasp_0" in result
    assert result["crawler_1"].level == 2


def test_resolve_many_with_active_techs():
    resolver = UnitStatsResolver()
    units = [_unit("marksmen", level=1, index=0)]
    techs = [{"unit": "marksmen", "tech": "Range enhancement"}]
    result = resolver.resolve_many(units, active_techs=techs)
    assert result["marksmen_0"].effective_range > get_combat_stats("marksmen").range


# ── Matchup scores ──────────────────────────────────────────────────────────


def test_anti_chaff_score_high_for_chaff_clear():
    resolver = UnitStatsResolver()
    vulcan = resolver.resolve_unit(_unit("vulcan", level=1))
    assert vulcan.anti_chaff_score > 1.0


def test_anti_heavy_score_high_for_single_target():
    resolver = UnitStatsResolver()
    marksmen = resolver.resolve_unit(_unit("marksmen", level=1))
    assert marksmen.anti_heavy_score > 1.0


def test_chaff_unit_low_anti_heavy():
    resolver = UnitStatsResolver()
    crawler = resolver.resolve_unit(_unit("crawler", level=1))
    assert crawler.anti_heavy_score < 0.5
