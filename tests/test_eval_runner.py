"""Tests for EvalRunner — deterministic pipeline, no LLM (Phase 7)."""

import json
from pathlib import Path
from unittest.mock import patch

from mechabellum_replay_parser.eval.cases import load_all_cases
from mechabellum_replay_parser.eval.runner import EvalResult, EvalRunner, _build_plans
from mechabellum_replay_parser.eval.report import format_report, save_report
from mechabellum_replay_parser.coach.schemas import (
    LegalAction,
    TacticalBundle,
    TacticalTheme,
)

_EVAL_CASES_DIR = Path(__file__).parent.parent / "eval_cases"


# ── _build_plans helper ───────────────────────────────────────────────────────


def _bundle(
    bundle_id: str,
    theme: TacticalTheme,
    required_action_ids: list[str],
    estimated_cost: int = 100,
) -> TacticalBundle:
    return TacticalBundle(
        id=bundle_id,
        title="Test bundle",
        theme=theme,
        target_threats=[],
        required_action_ids=required_action_ids,
        estimated_cost=estimated_cost,
        why_considered="test",
    )


def test_build_plans_empty_bundles_returns_fallback():
    plans = _build_plans([], [])
    assert len(plans) == 1
    assert plans[0].id == "eval_safe_default"


def test_build_plans_one_bundle_per_plan():
    bundle = _bundle("b1", TacticalTheme.ANTI_AIR_RESPONSE, ["buy_arclight_0"], 100)
    legal = [LegalAction(id="buy_arclight_0", type="buy_unit", unit="arclight", cost=100)]
    plans = _build_plans([bundle], legal)
    assert len(plans) == 1
    assert plans[0].id == "eval_b1"
    assert "buy_arclight_0" in plans[0].action_ids
    assert plans[0].total_cost == 100


def test_build_plans_uses_estimated_cost_when_no_legal_match():
    bundle = _bundle("b2", TacticalTheme.ANTI_CHAFF_CLEAR, ["buy_vulcan_0"], 150)
    plans = _build_plans([bundle], [])  # no legal actions
    assert plans[0].total_cost == 150


def test_build_plans_skips_bundle_without_required_actions():
    bundle = _bundle("b3", TacticalTheme.SAFE_DEFAULT, [], 0)
    plans = _build_plans([bundle], [])
    # empty required → skipped, fallback inserted
    assert len(plans) == 1
    assert plans[0].id == "eval_safe_default"


def test_build_plans_all_placements_empty():
    bundle = _bundle("b4", TacticalTheme.ANTI_AIR_RESPONSE, ["buy_arclight_0"], 100)
    plans = _build_plans([bundle], [])
    assert plans[0].placement == []


# ── EvalRunner — no LLM called ────────────────────────────────────────────────


def test_eval_runner_does_not_call_llm():
    """EvalRunner.run_case must complete without calling any LLM."""
    cases = load_all_cases(_EVAL_CASES_DIR)
    assert cases, "No eval cases found — check eval_cases/ directory"

    runner = EvalRunner()

    # Patch the LLMProvider to raise if instantiated — proves no LLM is needed
    with patch(
        "mechabellum_replay_parser.llm.client.LLMProvider",
        side_effect=AssertionError("LLM was called during eval"),
    ):
        result = runner.run_case(cases[0])

    assert isinstance(result, EvalResult)


def test_eval_runner_returns_eval_result():
    cases = load_all_cases(_EVAL_CASES_DIR)
    runner = EvalRunner()
    result = runner.run_case(cases[0])
    assert result.case_name == cases[0].name
    assert isinstance(result.scores.total, float)
    assert isinstance(result.passed, bool)
    assert isinstance(result.threat_keys_found, list)
    assert isinstance(result.bundle_themes_found, list)


# ── Air threat case ───────────────────────────────────────────────────────────


def test_air_threat_case_legality():
    """Case 001 must generate at least one valid plan."""
    cases = load_all_cases(_EVAL_CASES_DIR)
    air_case = next(c for c in cases if "air_threat" in c.name)
    runner = EvalRunner()
    result = runner.run_case(air_case)
    assert result.scores.legality == 1


def test_air_threat_case_detects_air_threat():
    """FeatureExtractor must detect the air threat key for case 001."""
    cases = load_all_cases(_EVAL_CASES_DIR)
    air_case = next(c for c in cases if "air_threat" in c.name)
    runner = EvalRunner()
    result = runner.run_case(air_case)
    assert "enemy_air_pressure" in result.threat_keys_found


# ── Chaff flood case ──────────────────────────────────────────────────────────


def test_chaff_flood_case_legality():
    """Case 002 must generate at least one valid plan."""
    cases = load_all_cases(_EVAL_CASES_DIR)
    chaff_case = next(c for c in cases if "chaff_flood" in c.name)
    runner = EvalRunner()
    result = runner.run_case(chaff_case)
    assert result.scores.legality == 1


def test_chaff_flood_case_detects_threat():
    """FeatureExtractor must detect the chaff overload key for case 002."""
    cases = load_all_cases(_EVAL_CASES_DIR)
    chaff_case = next(c for c in cases if "chaff_flood" in c.name)
    runner = EvalRunner()
    result = runner.run_case(chaff_case)
    assert "enemy_chaff_overload" in result.threat_keys_found


# ── Tower exposure case ───────────────────────────────────────────────────────


def test_tower_exposure_case_legality():
    """Case 003 must generate at least one valid plan."""
    cases = load_all_cases(_EVAL_CASES_DIR)
    tower_case = next(c for c in cases if "tower_exposure" in c.name)
    runner = EvalRunner()
    result = runner.run_case(tower_case)
    assert result.scores.legality == 1


# ── run_all ───────────────────────────────────────────────────────────────────


def test_run_all_returns_one_result_per_case():
    cases = load_all_cases(_EVAL_CASES_DIR)
    runner = EvalRunner()
    results = runner.run_all(cases)
    assert len(results) == len(cases)


def test_run_all_empty_list():
    runner = EvalRunner()
    assert runner.run_all([]) == []


# ── EvalResult model ──────────────────────────────────────────────────────────


def test_eval_result_passed_requires_legality_and_threats():
    """Demonstrates pass conditions are enforced by the runner."""
    cases = load_all_cases(_EVAL_CASES_DIR)
    runner = EvalRunner()
    for result in runner.run_all(cases):
        if result.passed:
            assert result.scores.legality == 1
            assert result.scores.main_threat_answered >= 3
        else:
            assert (
                result.scores.legality == 0
                or result.scores.main_threat_answered < 3
            )


# ── save_report / format_report ───────────────────────────────────────────────


def test_save_report_writes_json(tmp_path):
    cases = load_all_cases(_EVAL_CASES_DIR)
    runner = EvalRunner()
    results = runner.run_all(cases)
    out = save_report(results, path=tmp_path / "report.json")
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["total_cases"] == len(results)
    assert "cases" in data
    assert "pass_rate" in data


def test_format_report_contains_case_names():
    cases = load_all_cases(_EVAL_CASES_DIR)
    runner = EvalRunner()
    results = runner.run_all(cases)
    text = format_report(results)
    for r in results:
        assert r.case_name in text


def test_format_report_empty():
    text = format_report([])
    assert "0 cases" in text


def test_save_report_pass_rate_between_zero_and_one(tmp_path):
    cases = load_all_cases(_EVAL_CASES_DIR)
    runner = EvalRunner()
    results = runner.run_all(cases)
    out = save_report(results, path=tmp_path / "r.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert 0.0 <= data["pass_rate"] <= 1.0
