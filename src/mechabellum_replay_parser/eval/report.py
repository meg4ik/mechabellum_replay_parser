from __future__ import annotations

import json
from pathlib import Path

from .runner import EvalResult

_DEBUG_DIR = Path(".debug")


def save_report(results: list[EvalResult], path: Path | None = None) -> Path:
    out = path or (_DEBUG_DIR / "latest_eval_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "total_cases": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "pass_rate": (
            round(sum(1 for r in results if r.passed) / len(results), 3)
            if results
            else 0.0
        ),
        "cases": [r.model_dump() for r in results],
    }
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def format_report(results: list[EvalResult]) -> str:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    lines = [
        f"Eval Report  —  {total} cases  |  {passed} passed  |  {total - passed} failed",
        "",
    ]
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.append(
            f"  [{status}] {r.case_name}"
            f"  legality={r.scores.legality}"
            f"  threats={r.scores.main_threat_answered}/5"
            f"  total={r.scores.total:.0f}/30"
            + (f"  best_score={r.best_plan_score:.3f}" if r.best_plan_score else "")
        )
        for note in r.scores.notes:
            lines.append(f"         ! {note}")
    lines.append("")
    return "\n".join(lines)
