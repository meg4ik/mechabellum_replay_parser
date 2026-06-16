"""Tests for debug.report_builder — Markdown report generation (Phase 9)."""

import json
from pathlib import Path

from mechabellum_replay_parser.debug.report_builder import (
    _suspect_failure_stage,
    build_report,
    save_report,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _write_artifact(debug_dir: Path, name: str, data) -> None:
    debug_dir.mkdir(parents=True, exist_ok=True)
    (debug_dir / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _minimal_state_view() -> dict:
    return {
        "match_mode": "VS_1_1",
        "round": 5,
        "player_name": "Alice",
        "enemy_names": ["Bob"],
        "my_supply": 300,
        "my_state": {
            "name": "Alice",
            "hp": 20,
            "units": [{"name": "arclight", "index": 0}],
            "constructions": [],
        },
    }


def _full_artifacts(debug_dir: Path) -> None:
    _write_artifact(debug_dir, "latest_state_view.json", _minimal_state_view())
    _write_artifact(debug_dir, "latest_coordinate_frame.json", {
        "side": "negative_y", "front_y": -45, "back_y": -295, "x_min": -285, "x_max": 285
    })
    _write_artifact(debug_dir, "latest_features.json", {
        "threats": [{"key": "enemy_air_pressure", "severity": 0.8}],
        "tempo_state": "behind",
        "board_posture": "defensive",
    })
    _write_artifact(debug_dir, "latest_legal_actions.json", [
        {"id": "buy_arclight_0", "type": "buy_unit", "cost": 100},
        {"id": "keep_crawler_0", "type": "keep_unit", "cost": 0},
    ])
    _write_artifact(debug_dir, "latest_bundles.json", [
        {"id": "b1", "title": "Anti-air push", "theme": "anti_air_response",
         "estimated_cost": 100, "required_action_ids": ["buy_arclight_0"]}
    ])
    _write_artifact(debug_dir, "latest_planner_response.json", [
        {"id": "plan_a", "title": "Buy arclight", "action_ids": ["buy_arclight_0"],
         "total_cost": 100, "main_goal": "Counter air"}
    ])
    _write_artifact(debug_dir, "latest_validation.json", [
        {"plan_id": "plan_a", "is_valid": True, "issues": []}
    ])
    _write_artifact(debug_dir, "latest_plan_scores.json", [
        {"plan_id": "plan_a", "total_score": 0.72, "threat_coverage": 0.8,
         "supply_efficiency": 0.7, "legality_penalty": 0.0}
    ])
    _write_artifact(debug_dir, "latest_judge_response.json", {
        "best_plan_id": "plan_a", "confidence": 0.85, "main_reason": "Best anti-air"
    })
    _write_artifact(debug_dir, "latest_resolved_placement.json", [
        {"unit_name": "arclight", "x": 0, "y": -120, "lane": "center", "depth": "back"}
    ])
    _write_artifact(debug_dir, "latest_recommendation.json", {
        "summary": "Buy arclight to counter air threat.",
        "coach_text": "Your army lacks anti-air.",
        "placement": [{"unit": "arclight", "x": 0, "y": -120}],
    })
    _write_artifact(debug_dir, "latest_timings.json", {
        "state_view_ms": 2, "features_ms": 5, "planner_llm_ms": 1200, "judge_llm_ms": 800
    })
    _write_artifact(debug_dir, "latest_constructions.json", [])


# ── build_report basic structure ──────────────────────────────────────────────


def test_build_report_returns_string(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert isinstance(report, str)
    assert len(report) > 100


def test_report_has_all_sections(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    expected_sections = [
        "## Replay / Round",
        "## Coordinate Frame",
        "## Main Threats",
        "## Legal Actions",
        "## Tactical Bundles",
        "## Planner Plans",
        "## Validation Errors",
        "## Resolved Placement",
        "## Plan Scores",
        "## Judge Selection",
        "## Final Recommendation",
        "## Stage Timings",
        "## Suspected Failure Stage",
    ]
    for section in expected_sections:
        assert section in report, f"Missing section: {section!r}"


def test_report_contains_round_and_player(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert "Round" in report
    assert "5" in report
    assert "Alice" in report


def test_report_contains_threats(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert "enemy_air_pressure" in report


def test_report_contains_legal_actions(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert "buy_arclight_0" in report


def test_report_contains_plan_score(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert "plan_a" in report
    assert "0.720" in report or "0.72" in report


def test_report_contains_judge_selection(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert "plan_a" in report
    assert "Best anti-air" in report


def test_report_contains_timings(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert "planner_llm_ms" in report
    assert "1200" in report


def test_report_contains_coordinate_frame(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert "negative_y" in report
    assert "-45" in report


def test_report_title(tmp_path):
    _full_artifacts(tmp_path)
    report = build_report(tmp_path)
    assert "# Latest Recommendation Debug Report" in report


# ── Missing artifacts graceful handling ───────────────────────────────────────


def test_empty_debug_dir(tmp_path):
    report = build_report(tmp_path)
    assert "## Replay / Round" in report
    assert "No state_view artifact" in report


def test_missing_single_artifact(tmp_path):
    _full_artifacts(tmp_path)
    (tmp_path / "latest_features.json").unlink()
    report = build_report(tmp_path)
    assert "No features artifact" in report


def test_corrupted_json_handled(tmp_path):
    _full_artifacts(tmp_path)
    (tmp_path / "latest_plan_scores.json").write_text("NOT JSON{{{{", encoding="utf-8")
    report = build_report(tmp_path)
    assert "## Plan Scores" in report


# ── save_report ───────────────────────────────────────────────────────────────


def test_save_report_writes_file(tmp_path):
    _full_artifacts(tmp_path)
    out = save_report(tmp_path)
    assert out == tmp_path / "latest_failure_report.md"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "## Replay / Round" in content


def test_save_report_creates_dir(tmp_path):
    nested = tmp_path / "sub" / "debug"
    out = save_report(nested)
    assert out.exists()


# ── _suspect_failure_stage ────────────────────────────────────────────────────


def _full_data() -> dict:
    return {
        "state_view": _minimal_state_view(),
        "features": {"threats": [{"key": "enemy_air_pressure", "severity": 0.8}]},
        "legal_actions": [{"id": "buy_arclight_0"}],
        "bundles": [{"id": "b1"}],
        "plans": [{"id": "plan_a"}],
        "validation": [{"plan_id": "plan_a", "is_valid": True, "issues": []}],
        "plan_scores": [{"plan_id": "plan_a", "total_score": 0.7}],
        "judge": {"best_plan_id": "plan_a", "confidence": 0.85},
        "resolved_placement": [{"unit_name": "arclight", "x": 0, "y": -120}],
        "recommendation": {"summary": "Buy arclight"},
        "coordinate_frame": None,
        "constructions": None,
        "timings": None,
    }


def test_suspect_no_failure():
    data = _full_data()
    result = _suspect_failure_stage(data)
    assert "No obvious failure" in result


def test_suspect_no_state_view():
    data = _full_data()
    data["state_view"] = None
    result = _suspect_failure_stage(data)
    assert "state_view" in result.lower() or "parser" in result.lower()


def test_suspect_no_threats():
    data = _full_data()
    data["features"] = {"threats": [], "tempo_state": "even"}
    result = _suspect_failure_stage(data)
    assert "feature_extractor" in result


def test_suspect_no_legal_actions():
    data = _full_data()
    data["legal_actions"] = []
    result = _suspect_failure_stage(data)
    assert "legal_action_generator" in result


def test_suspect_no_bundles():
    data = _full_data()
    data["bundles"] = []
    result = _suspect_failure_stage(data)
    assert "tactical_bundle_generator" in result


def test_suspect_no_plans():
    data = _full_data()
    data["plans"] = []
    result = _suspect_failure_stage(data)
    assert "planner_llm" in result


def test_suspect_all_plans_invalid():
    data = _full_data()
    data["validation"] = [
        {"plan_id": "plan_a", "is_valid": False, "issues": [{"message": "over budget"}]}
    ]
    result = _suspect_failure_stage(data)
    assert "validator" in result


def test_suspect_no_judge_selection():
    data = _full_data()
    data["judge"] = {"best_plan_id": None, "confidence": 0}
    result = _suspect_failure_stage(data)
    assert "judge_llm" in result


def test_suspect_no_resolved_placement():
    data = _full_data()
    data["resolved_placement"] = []
    result = _suspect_failure_stage(data)
    assert "placement_resolver" in result


def test_suspect_very_low_scores():
    data = _full_data()
    data["plan_scores"] = [{"plan_id": "plan_a", "total_score": 0.02}]
    # threshold is < 0.1 → plan_scorer
    result = _suspect_failure_stage(data)
    assert "plan_scorer" in result
