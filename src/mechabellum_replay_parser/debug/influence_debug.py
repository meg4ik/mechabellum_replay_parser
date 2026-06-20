"""Write influence-specific debug artifacts (CSV, Markdown)."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from ..coach.influence_map import InfluenceMapResult
from ..coach.influence_schemas import InfluenceAnalysisSummary


def write_influence_csv(
    influence: InfluenceMapResult,
    debug_dir: Path,
) -> None:
    channels = {
        "my_ground": influence.arrays.my_ground,
        "enemy_ground": influence.arrays.enemy_ground,
        "my_air": influence.arrays.my_air,
        "enemy_air": influence.arrays.enemy_air,
    }
    for name, arr in channels.items():
        path = debug_dir / f"latest_influence_{name}.csv"
        buf = io.StringIO()
        writer = csv.writer(buf)
        for row in arr:
            writer.writerow([f"{v:.4f}" for v in row])
        path.write_text(buf.getvalue(), encoding="utf-8")


def write_influence_plan_deltas(
    plan_scores: list[dict],
    debug_dir: Path,
) -> None:
    path = debug_dir / "latest_influence_plan_deltas.json"
    deltas = []
    for s in plan_scores:
        if s.get("influence_improvement", 0) or s.get("influence_explanation"):
            deltas.append(
                {
                    "plan_id": s.get("plan_id"),
                    "influence_improvement": s.get("influence_improvement", 0),
                    "anti_air_improvement": s.get("anti_air_improvement", 0),
                    "anti_chaff_improvement": s.get("anti_chaff_improvement", 0),
                    "anti_heavy_improvement": s.get("anti_heavy_improvement", 0),
                    "artillery_risk_reduction": s.get("artillery_risk_reduction", 0),
                    "influence_explanation": s.get("influence_explanation", []),
                }
            )
    path.write_text(
        json.dumps(deltas, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_influence_report(
    summary: InfluenceAnalysisSummary | None,
    plan_scores: list[dict] | None = None,
) -> str:
    if not summary:
        return "> *No influence data available.*"

    parts: list[str] = []

    ga = summary.global_assessment
    if ga:
        lines = [f"- **{k}:** {v}" for k, v in ga.items()]
        parts.append("### Global Assessment\n\n" + "\n".join(lines))

    if summary.tactical_findings:
        header = "| Severity | Key | Zone | Evidence | Response types |"
        sep = "|---:|---|---|---|---|"
        rows = []
        for f in summary.tactical_findings:
            zone_str = f.zone.value if f.zone else "—"
            resp = (
                ", ".join(f.recommended_response_types)
                if f.recommended_response_types
                else "—"
            )
            rows.append(
                f"| {f.severity:.2f} | {f.key} | {zone_str} | {f.evidence} | {resp} |"
            )
        parts.append("### Critical Findings\n\n" + "\n".join([header, sep, *rows]))

    if summary.zones:
        header = "| Zone | My Ground | Enemy Ground | My Air | Enemy Air | Danger |"
        sep = "|---|---:|---:|---:|---:|---:|"
        rows = []
        for z in summary.zones:
            rows.append(
                f"| {z.zone.value} | {z.my_ground:.2f} | {z.enemy_ground:.2f}"
                f" | {z.my_air:.2f} | {z.enemy_air:.2f} | {z.danger_for_my_ground:.2f} |"
            )
        parts.append("### Zone Summary\n\n" + "\n".join([header, sep, *rows]))

    if plan_scores:
        header = "| Plan | Total Score | Influence Improvement | Anti-Air | Safety | Explanation |"
        sep = "|---|---:|---:|---:|---:|---|"
        rows = []
        for s in plan_scores:
            expl = "; ".join(s.get("influence_explanation", []))[:80] or "—"
            rows.append(
                f"| {s.get('plan_id', '?')} | {s.get('total_score', 0):.3f}"
                f" | {s.get('influence_improvement', 0):.2f}"
                f" | {s.get('anti_air_improvement', 0):.2f}"
                f" | {s.get('positioning_safety', 0):.2f}"
                f" | {expl} |"
            )
        parts.append("### Candidate Plan Deltas\n\n" + "\n".join([header, sep, *rows]))

    return "\n\n".join(parts) if parts else "> *No influence findings.*"
