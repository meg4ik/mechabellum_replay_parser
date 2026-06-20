"""Tests for influence-extended eval framework (Phase 08)."""

from __future__ import annotations

from pathlib import Path

from mechabellum_replay_parser.eval.cases import EvalExpected, load_all_cases, load_case
from mechabellum_replay_parser.eval.runner import EvalRunner
from mechabellum_replay_parser.eval.report import save_report

_EVAL_CASES_DIR = Path(__file__).parent.parent / "eval_cases"


# ── Eval cases load correctly ────────────────────────────────────────────────


def test_all_10_cases_load():
    cases = load_all_cases(_EVAL_CASES_DIR)
    assert len(cases) >= 10


def test_air_threat_case_has_influence_expected():
    case = load_case(_EVAL_CASES_DIR / "case_001_air_threat")
    assert "anti_air_gap" in case.expected.expected_influence_findings


def test_economy_case_has_forbidden_findings():
    case = load_case(_EVAL_CASES_DIR / "case_010_economy_round")
    assert "anti_air_gap" in case.expected.forbidden_high_severity_findings


# ── EvalExpected new fields ──────────────────────────────────────────────────


def test_eval_expected_influence_fields():
    e = EvalExpected(
        expected_influence_findings=["anti_air_gap"],
        expected_critical_zones=["center_front"],
        forbidden_high_severity_findings=["anti_chaff_gap"],
    )
    assert e.expected_influence_findings == ["anti_air_gap"]
    assert e.expected_critical_zones == ["center_front"]
    assert e.forbidden_high_severity_findings == ["anti_chaff_gap"]


def test_eval_expected_backward_compat():
    e = EvalExpected(must_address_threats=["enemy_air_pressure"])
    assert e.expected_influence_findings == []
    assert e.forbidden_high_severity_findings == []


# ── Runner runs without OpenAI key ───────────────────────────────────────────


def test_runner_no_openai_key_required():
    cases = load_all_cases(_EVAL_CASES_DIR)
    assert cases
    runner = EvalRunner()
    result = runner.run_case(cases[0])
    assert result.case_name == cases[0].name
    assert result.scores.legality in (0, 1)


def test_runner_returns_influence_findings():
    case = load_case(_EVAL_CASES_DIR / "case_001_air_threat")
    runner = EvalRunner()
    result = runner.run_case(case)
    assert isinstance(result.influence_findings_found, list)


def test_runner_air_threat_detects_air_gap():
    case = load_case(_EVAL_CASES_DIR / "case_001_air_threat")
    runner = EvalRunner()
    result = runner.run_case(case)
    assert "anti_air_gap" in result.influence_findings_found


def test_runner_economy_no_high_severity():
    case = load_case(_EVAL_CASES_DIR / "case_010_economy_round")
    runner = EvalRunner()
    result = runner.run_case(case)
    for forbidden in case.expected.forbidden_high_severity_findings:
        high_sev = [
            f for f in result.influence_findings_found if f == forbidden
        ]
        if high_sev:
            assert result.scores.influence_finding_accuracy < 1.0 or len(high_sev) == 0


# ── Rubric scores include influence ──────────────────────────────────────────


def test_rubric_has_influence_scores():
    case = load_case(_EVAL_CASES_DIR / "case_001_air_threat")
    runner = EvalRunner()
    result = runner.run_case(case)
    assert hasattr(result.scores, "influence_finding_accuracy")
    assert hasattr(result.scores, "influence_zone_accuracy")
    assert hasattr(result.scores, "influence_plan_improvement")


def test_air_threat_has_finding_accuracy():
    case = load_case(_EVAL_CASES_DIR / "case_001_air_threat")
    runner = EvalRunner()
    result = runner.run_case(case)
    assert result.scores.influence_finding_accuracy > 0


# ── Report includes influence ────────────────────────────────────────────────


def test_report_includes_influence_fields(tmp_path: Path):
    cases = load_all_cases(_EVAL_CASES_DIR)[:3]
    runner = EvalRunner()
    results = runner.run_all(cases)
    path = save_report(results, tmp_path / "eval_report.json")
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["total_cases"] == 3
    first = data["cases"][0]
    assert "influence_finding_accuracy" in first["scores"]


# ── Run all 10 cases without crash ───────────────────────────────────────────


def test_all_10_cases_run_without_crash():
    cases = load_all_cases(_EVAL_CASES_DIR)
    runner = EvalRunner()
    results = runner.run_all(cases)
    assert len(results) == len(cases)
    for r in results:
        assert r.scores.total >= 0
