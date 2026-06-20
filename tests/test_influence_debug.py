from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from mechabellum_replay_parser.coach.influence_map import InfluenceMapArrays, InfluenceMapResult
from mechabellum_replay_parser.coach.influence_schemas import (
    InfluenceAnalysisSummary,
    InfluenceGridSpec,
    MapZone,
    TacticalInfluenceFinding,
    ZoneInfluenceSummary,
)
from mechabellum_replay_parser.debug.influence_debug import (
    build_influence_report,
    write_influence_csv,
    write_influence_plan_deltas,
)
from mechabellum_replay_parser.debug.report_builder import build_report


def _grid() -> InfluenceGridSpec:
    return InfluenceGridSpec(x_min=-300, x_max=300, y_front=-10, y_back=-310, width=5, height=4, player_side="negative_y")


def _finding(key="anti_air_gap", severity=0.8) -> TacticalInfluenceFinding:
    return TacticalInfluenceFinding(
        key=key, severity=severity, zone=MapZone.RIGHT_FRONT,
        evidence="Test evidence.", recommended_response_types=["add_anti_air"],
    )


def _summary(findings=None) -> InfluenceAnalysisSummary:
    return InfluenceAnalysisSummary(
        grid=_grid(),
        global_assessment={"ground_balance": "enemy_favored", "artillery_pressure": "high"},
        zones=[ZoneInfluenceSummary(zone=z, my_ground=0.3, enemy_ground=0.6) for z in MapZone],
        critical_zones=[ZoneInfluenceSummary(zone=MapZone.CENTER_FRONT, danger_for_my_ground=0.7)],
        tactical_findings=findings or [_finding()],
    )


def _influence_result() -> InfluenceMapResult:
    shape = (4, 5)
    return InfluenceMapResult(
        grid=_grid(),
        arrays=InfluenceMapArrays(
            my_ground=np.ones(shape) * 0.5,
            enemy_ground=np.ones(shape) * 0.8,
            my_air=np.zeros(shape),
            enemy_air=np.ones(shape) * 0.3,
            my_anti_chaff=np.zeros(shape),
            enemy_anti_chaff=np.zeros(shape),
            my_anti_heavy=np.zeros(shape),
            enemy_anti_heavy=np.zeros(shape),
            my_artillery=np.zeros(shape),
            enemy_artillery=np.zeros(shape),
            my_durability=np.zeros(shape),
            enemy_durability=np.zeros(shape),
        ),
    )


def _plan_scores():
    return [
        {
            "plan_id": "p1",
            "total_score": 0.7,
            "influence_improvement": 0.6,
            "anti_air_improvement": 0.5,
            "anti_chaff_improvement": 0.0,
            "anti_heavy_improvement": 0.0,
            "artillery_risk_reduction": 0.0,
            "positioning_safety": 0.6,
            "influence_explanation": ["Addresses anti-air gap."],
        },
        {
            "plan_id": "p2",
            "total_score": 0.4,
            "influence_improvement": 0.0,
            "anti_air_improvement": 0.0,
            "anti_chaff_improvement": 0.0,
            "anti_heavy_improvement": 0.0,
            "artillery_risk_reduction": 0.0,
            "positioning_safety": 0.5,
            "influence_explanation": [],
        },
    ]


# ── Influence report Markdown ────────────────────────────────────────────────


def test_build_influence_report_has_sections():
    report = build_influence_report(_summary(), _plan_scores())
    assert "Global Assessment" in report
    assert "Critical Findings" in report
    assert "Zone Summary" in report
    assert "Candidate Plan Deltas" in report


def test_build_influence_report_has_finding_data():
    report = build_influence_report(_summary())
    assert "anti_air_gap" in report
    assert "0.80" in report
    assert "right_front" in report


def test_build_influence_report_none_summary():
    report = build_influence_report(None)
    assert "No influence data" in report


def test_build_influence_report_empty_findings():
    summary = InfluenceAnalysisSummary(grid=_grid())
    report = build_influence_report(summary)
    assert isinstance(report, str)


# ── CSV export ───────────────────────────────────────────────────────────────


def test_write_influence_csv(tmp_path: Path):
    result = _influence_result()
    write_influence_csv(result, tmp_path)

    for name in ("my_ground", "enemy_ground", "my_air", "enemy_air"):
        csv_path = tmp_path / f"latest_influence_{name}.csv"
        assert csv_path.exists()
        content = csv_path.read_text(encoding="utf-8")
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) == 4


def test_csv_shape_matches_grid(tmp_path: Path):
    result = _influence_result()
    write_influence_csv(result, tmp_path)
    content = (tmp_path / "latest_influence_my_ground.csv").read_text(encoding="utf-8")
    lines = [line for line in content.strip().split("\n") if line]
    assert len(lines) == 4
    cols = lines[0].split(",")
    assert len(cols) == 5


# ── Plan deltas JSON ─────────────────────────────────────────────────────────


def test_write_influence_plan_deltas(tmp_path: Path):
    write_influence_plan_deltas(_plan_scores(), tmp_path)
    path = tmp_path / "latest_influence_plan_deltas.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["plan_id"] == "p1"
    assert data[0]["influence_improvement"] == 0.6


# ── Report builder integration ───────────────────────────────────────────────


def test_report_builder_handles_missing_influence(tmp_path: Path):
    (tmp_path / "latest_state_view.json").write_text("{}", encoding="utf-8")
    (tmp_path / "latest_features.json").write_text("{}", encoding="utf-8")
    report = build_report(tmp_path)
    assert "Influence Analysis" in report
    assert "No influence data" in report


def test_report_builder_includes_influence_section(tmp_path: Path):
    (tmp_path / "latest_state_view.json").write_text("{}", encoding="utf-8")
    (tmp_path / "latest_features.json").write_text("{}", encoding="utf-8")
    findings = _summary().model_dump(mode="json")
    (tmp_path / "latest_influence_findings.json").write_text(
        json.dumps(findings), encoding="utf-8",
    )
    report = build_report(tmp_path)
    assert "Influence Analysis" in report
    assert "enemy_favored" in report
