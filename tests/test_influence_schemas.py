from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from mechabellum_replay_parser.coach.influence_schemas import (
    InfluenceAnalysisSummary,
    InfluenceChannel,
    InfluenceGridSpec,
    MapZone,
    TacticalInfluenceFinding,
    ZoneInfluenceSummary,
)


# ── Enum tests ──────────────────────────────────────────────────────────────


def test_influence_channel_values():
    assert InfluenceChannel.MY_GROUND == "my_ground"
    assert InfluenceChannel.ENEMY_AIR == "enemy_air"
    assert len(InfluenceChannel) == 12


def test_map_zone_values():
    assert MapZone.LEFT_FRONT == "left_front"
    assert MapZone.CENTER_MID == "center_mid"
    assert MapZone.RIGHT_BACK == "right_back"
    assert len(MapZone) == 9


# ── InfluenceGridSpec ───────────────────────────────────────────────────────


def _grid() -> InfluenceGridSpec:
    return InfluenceGridSpec(
        x_min=-300, x_max=300, y_front=-10, y_back=-310,
        width=30, height=20, player_side="negative_y",
    )


def test_grid_spec_serializes():
    g = _grid()
    data = g.model_dump(mode="json")
    s = json.dumps(data)
    loaded = json.loads(s)
    assert loaded["width"] == 30
    assert loaded["player_side"] == "negative_y"


# ── ZoneInfluenceSummary ────────────────────────────────────────────────────


def test_zone_summary_defaults():
    z = ZoneInfluenceSummary(zone=MapZone.CENTER_FRONT)
    assert z.my_ground == 0.0
    assert z.enemy_ground == 0.0
    assert z.opportunity_score == 0.0


def test_zone_summary_valid_values():
    z = ZoneInfluenceSummary(
        zone=MapZone.LEFT_MID,
        my_ground=0.5, enemy_ground=0.8,
        my_air=0.0, enemy_air=0.9,
        my_anti_chaff=0.3, enemy_anti_chaff=0.2,
        my_anti_heavy=0.1, enemy_anti_heavy=0.7,
        danger_for_my_ground=0.6, danger_for_my_air=0.85,
        opportunity_score=0.4,
    )
    assert z.danger_for_my_air == 0.85


def test_zone_summary_rejects_out_of_bounds():
    with pytest.raises(ValidationError):
        ZoneInfluenceSummary(zone=MapZone.CENTER_FRONT, my_ground=1.5)
    with pytest.raises(ValidationError):
        ZoneInfluenceSummary(zone=MapZone.CENTER_FRONT, enemy_air=-0.1)


def test_zone_summary_clamped_factory():
    z = ZoneInfluenceSummary.clamped(
        zone=MapZone.RIGHT_BACK,
        my_ground=1.5,
        enemy_ground=-0.3,
        opportunity_score=0.7,
    )
    assert z.my_ground == 1.0
    assert z.enemy_ground == 0.0
    assert z.opportunity_score == 0.7


def test_zone_summary_serializes():
    z = ZoneInfluenceSummary(zone=MapZone.CENTER_MID, my_ground=0.5)
    data = z.model_dump(mode="json")
    s = json.dumps(data)
    loaded = json.loads(s)
    assert loaded["zone"] == "center_mid"
    assert loaded["my_ground"] == 0.5


# ── TacticalInfluenceFinding ────────────────────────────────────────────────


def test_finding_basic():
    f = TacticalInfluenceFinding(
        key="anti_air_gap",
        severity=0.82,
        zone=MapZone.RIGHT_FRONT,
        evidence="Enemy air high on right, my anti-air low.",
        recommended_response_types=["add_anti_air", "shift_anti_air"],
    )
    assert f.severity == 0.82
    assert f.zone == MapZone.RIGHT_FRONT
    assert len(f.recommended_response_types) == 2


def test_finding_no_zone():
    f = TacticalInfluenceFinding(
        key="global_ground_deficit",
        severity=0.5,
        evidence="Global ground pressure is enemy-favored.",
    )
    assert f.zone is None


def test_finding_rejects_severity_out_of_bounds():
    with pytest.raises(ValidationError):
        TacticalInfluenceFinding(key="x", severity=1.5, evidence="bad")
    with pytest.raises(ValidationError):
        TacticalInfluenceFinding(key="x", severity=-0.1, evidence="bad")


def test_finding_serializes():
    f = TacticalInfluenceFinding(
        key="artillery_danger",
        severity=0.9,
        zone=MapZone.CENTER_BACK,
        evidence="Enemy artillery overlaps my backline.",
        recommended_response_types=["spread_backline"],
        forbidden_response_types=["clump_backline"],
    )
    data = f.model_dump(mode="json")
    s = json.dumps(data)
    loaded = json.loads(s)
    assert loaded["key"] == "artillery_danger"
    assert loaded["severity"] == 0.9
    assert "spread_backline" in loaded["recommended_response_types"]
    assert "clump_backline" in loaded["forbidden_response_types"]


# ── InfluenceAnalysisSummary ────────────────────────────────────────────────


def test_summary_minimal():
    summary = InfluenceAnalysisSummary(grid=_grid())
    assert summary.version == "v1"
    assert summary.zones == []
    assert summary.tactical_findings == []


def test_summary_full():
    zone1 = ZoneInfluenceSummary(zone=MapZone.CENTER_FRONT, my_ground=0.6, enemy_ground=0.8)
    finding = TacticalInfluenceFinding(
        key="anti_air_gap", severity=0.7, evidence="test",
    )
    summary = InfluenceAnalysisSummary(
        grid=_grid(),
        global_assessment={"ground_balance": "enemy_favored_center"},
        zones=[zone1],
        critical_zones=[zone1],
        tactical_findings=[finding],
    )
    assert len(summary.zones) == 1
    assert len(summary.tactical_findings) == 1
    assert summary.global_assessment["ground_balance"] == "enemy_favored_center"


def test_summary_serializes():
    zone = ZoneInfluenceSummary(zone=MapZone.LEFT_FRONT, my_ground=0.3)
    finding = TacticalInfluenceFinding(
        key="flank_opportunity", severity=0.6,
        zone=MapZone.LEFT_FRONT, evidence="Enemy weak on left.",
    )
    summary = InfluenceAnalysisSummary(
        grid=_grid(),
        global_assessment={"air_balance": "neutral"},
        zones=[zone],
        critical_zones=[],
        tactical_findings=[finding],
    )
    data = summary.model_dump(mode="json")
    s = json.dumps(data)
    loaded = json.loads(s)
    assert loaded["version"] == "v1"
    assert loaded["grid"]["width"] == 30
    assert len(loaded["zones"]) == 1
    assert loaded["tactical_findings"][0]["key"] == "flank_opportunity"


def test_no_numpy_in_schemas():
    """Public schemas must not depend on numpy."""
    import mechabellum_replay_parser.coach.influence_schemas as mod
    source = open(mod.__file__, encoding="utf-8").read()
    assert "numpy" not in source
    assert "np." not in source
