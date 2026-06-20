"""Build a human-readable Markdown debug report from `.debug/` artifacts.

Does NOT call the LLM — reads existing artifact files only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEBUG_DIR = Path(".debug")

_ARTIFACT_FILES = {
    "state_view": "latest_state_view.json",
    "features": "latest_features.json",
    "legal_actions": "latest_legal_actions.json",
    "bundles": "latest_bundles.json",
    "plans": "latest_planner_response.json",
    "validation": "latest_validation.json",
    "plan_scores": "latest_plan_scores.json",
    "judge": "latest_judge_response.json",
    "resolved_placement": "latest_resolved_placement.json",
    "recommendation": "latest_recommendation.json",
    "coordinate_frame": "latest_coordinate_frame.json",
    "constructions": "latest_constructions.json",
    "timings": "latest_timings.json",
    "influence_findings": "latest_influence_findings.json",
    "influence_map_summary": "latest_influence_map_summary.json",
}


def _load(debug_dir: Path, key: str) -> Any:
    path = debug_dir / _ARTIFACT_FILES[key]
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _fmt_json(obj: Any, indent: int = 2) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent, default=str)


def _section(title: str, body: str) -> str:
    return f"## {title}\n\n{body.strip()}\n\n"


# ── Suspected failure stage ───────────────────────────────────────────────────


def _suspect_failure_stage(data: dict[str, Any]) -> str:
    sv = data.get("state_view") or {}
    features = data.get("features") or {}
    legal = data.get("legal_actions") or []
    bundles = data.get("bundles") or []
    plans = data.get("plans") or []
    validation = data.get("validation") or []
    scores = data.get("plan_scores") or []
    judge = data.get("judge") or {}
    placement = data.get("resolved_placement") or []
    rec = data.get("recommendation") or {}

    if not sv:
        return "**parser / state_view** — no state_view artifact"
    if not features.get("threats"):
        return "**feature_extractor** — no threats detected (check FeatureExtractor signals)"
    if not legal:
        return "**legal_action_generator** — no legal actions produced"
    if not bundles:
        return "**tactical_bundle_generator** — no bundles generated"
    if not plans:
        return "**planner_llm** — no plans returned (LLM timeout or parse failure)"
    if validation and all(not v.get("is_valid") for v in validation):
        return "**validator** — all plans failed validation (check action_ids vs legal_actions)"
    if scores:
        best_score = max((s.get("total_score", 0) for s in scores), default=0)
        if best_score < 0.1:
            return "**plan_scorer** — all plan scores near zero (check threat coverage / supply)"
    if not judge.get("best_plan_id"):
        return "**judge_llm** — no plan selected (LLM timeout or invalid selection)"
    if not placement and plans:
        return (
            "**placement_resolver** — no resolved placements "
            "(missing placement_intents or out-of-bounds)"
        )
    if not rec.get("summary"):
        return "**recommendation_builder** — empty recommendation summary"
    return "No obvious failure detected — recommendation looks complete"


# ── Section builders ──────────────────────────────────────────────────────────


def _section_replay_round(sv: dict | None) -> str:
    if not sv:
        return "> *No state_view artifact found.*"
    lines = [
        f"- **Match mode:** {sv.get('match_mode', '—')}",
        f"- **Round:** {sv.get('round', '—')}",
        f"- **Player:** {sv.get('player_name', '—')}",
        f"- **Enemies:** {', '.join(sv.get('enemy_names', []))}",
        f"- **Supply:** {sv.get('my_supply', '—')}",
    ]
    my = sv.get("my_state", {})
    if my:
        lines.append(f"- **My HP:** {my.get('hp', '—')}")
        lines.append(f"- **My units:** {[u.get('name') for u in my.get('units', [])]}")
    return "\n".join(lines)


def _section_coordinate_frame(cf: dict | None) -> str:
    if not cf:
        return "> *No coordinate_frame artifact.*"
    return (
        f"- **Side:** {cf.get('side', '—')}\n"
        f"- **Front Y:** {cf.get('front_y', '—')}\n"
        f"- **Back Y:** {cf.get('back_y', '—')}\n"
        f"- **X range:** [{cf.get('x_min', '—')} .. {cf.get('x_max', '—')}]"
    )


def _section_threats(features: dict | None) -> str:
    if not features:
        return "> *No features artifact.*"
    threats = features.get("threats", [])
    if not threats:
        return "> *No threats detected.*"
    lines = [
        f"- **{t.get('key', '?')}** — severity={t.get('severity', '?')}"
        for t in threats
    ]
    lines.append(
        f"\nTempo: `{features.get('tempo_state', '—')}`  |  Posture: `{features.get('board_posture', '—')}`"
    )
    return "\n".join(lines)


def _section_legal_actions(legal: list | None) -> str:
    if not legal:
        return "> *No legal actions.*"
    lines = [
        f"- `{a.get('id', '?')}` ({a.get('type', '?')}) cost={a.get('cost', 0)}"
        for a in legal[:20]
    ]
    if len(legal) > 20:
        lines.append(f"… and {len(legal) - 20} more")
    return "\n".join(lines)


def _section_bundles(bundles: list | None) -> str:
    if not bundles:
        return "> *No tactical bundles.*"
    lines = []
    for b in bundles:
        lines.append(
            f"- **{b.get('title', '?')}** (theme=`{b.get('theme', '?')}`)"
            f"  cost={b.get('estimated_cost', '?')}"
            f"  actions={b.get('required_action_ids', [])}"
        )
    return "\n".join(lines)


def _section_plans(plans: list | None) -> str:
    if not plans:
        return "> *No planner plans.*"
    lines = []
    for p in plans:
        lines.append(
            f"- **[{p.get('id', '?')}]** {p.get('title', '?')}"
            f"  cost={p.get('total_cost', '?')}"
            f"  actions={p.get('action_ids', [])}"
        )
    return "\n".join(lines)


def _section_validation(validation: list | None) -> str:
    if not validation:
        return "> *No validation data.*"
    lines = []
    for v in validation:
        status = "✓" if v.get("is_valid") else "✗"
        lines.append(f"- {status} `{v.get('plan_id', '?')}`")
        for issue in v.get("issues", []):
            lines.append(
                f"  - [{issue.get('severity', '?')}] {issue.get('message', '?')}"
            )
    return "\n".join(lines)


def _section_resolved_placement(placement: list | None) -> str:
    if not placement:
        return "> *No resolved placements.*"
    lines = []
    for r in placement:
        lines.append(
            f"- {r.get('unit_name', '?')}  x={r.get('x', '?')} y={r.get('y', '?')}"
            f"  lane={r.get('lane', '?')} depth={r.get('depth', '?')}"
        )
    return "\n".join(lines)


def _section_plan_scores(scores: list | None) -> str:
    if not scores:
        return "> *No plan score data.*"
    lines = []
    for s in scores:
        lines.append(
            f"- `{s.get('plan_id', '?')}`"
            f"  total={s.get('total_score', 0):.3f}"
            f"  threats={s.get('threat_coverage', 0):.2f}"
            f"  supply={s.get('supply_efficiency', 0):.2f}"
            f"  legality_penalty={s.get('legality_penalty', 0):.2f}"
        )
    return "\n".join(lines)


def _section_judge(judge: dict | None) -> str:
    if not judge:
        return "> *No judge output.*"
    lines = [
        f"- **Selected plan:** `{judge.get('best_plan_id', '—')}`",
        f"- **Confidence:** {judge.get('confidence', '—')}",
        f"- **Main reason:** {judge.get('main_reason', '—')}",
    ]
    return "\n".join(lines)


def _section_recommendation(rec: dict | None) -> str:
    if not rec:
        return "> *No recommendation artifact.*"
    lines = [
        f"**Summary:** {rec.get('summary', '—')}",
        "",
        f"**Coach text:**\n{rec.get('coach_text', '—')}",
        "",
        f"**Placement items:** {len(rec.get('placement') or [])}",
    ]
    return "\n".join(lines)


def _section_timings(timings: dict | None) -> str:
    if not timings:
        return "> *No timing data.*"
    lines = [f"- `{k}`: {v} ms" for k, v in timings.items()]
    return "\n".join(lines)


def _section_influence(
    findings_data: dict | None,
    plan_scores: list | None,
) -> str:
    if not findings_data:
        return "> *No influence data available.*"

    parts: list[str] = []

    ga = findings_data.get("global_assessment", {})
    if ga:
        lines = [f"- **{k}:** {v}" for k, v in ga.items()]
        parts.append("**Global Assessment:**\n" + "\n".join(lines))

    tf = findings_data.get("tactical_findings", [])
    if tf:
        header = "| Severity | Key | Zone | Evidence |"
        sep = "|---:|---|---|---|"
        rows = []
        for f in tf:
            zone = f.get("zone") or "—"
            rows.append(
                f"| {f.get('severity', 0):.2f} | {f.get('key', '?')} | {zone} | {f.get('evidence', '—')} |"
            )
        parts.append("**Tactical Findings:**\n" + "\n".join([header, sep, *rows]))

    if plan_scores:
        has_influence = any(s.get("influence_improvement", 0) for s in plan_scores)
        if has_influence:
            header = "| Plan | Influence | Anti-Air | Anti-Chaff | Anti-Heavy |"
            sep = "|---|---:|---:|---:|---:|"
            rows = []
            for s in plan_scores:
                rows.append(
                    f"| {s.get('plan_id', '?')}"
                    f" | {s.get('influence_improvement', 0):.2f}"
                    f" | {s.get('anti_air_improvement', 0):.2f}"
                    f" | {s.get('anti_chaff_improvement', 0):.2f}"
                    f" | {s.get('anti_heavy_improvement', 0):.2f} |"
                )
            parts.append(
                "**Plan Influence Deltas:**\n" + "\n".join([header, sep, *rows])
            )

    return "\n\n".join(parts) if parts else "> *No influence findings.*"


# ── Public API ────────────────────────────────────────────────────────────────


def build_report(debug_dir: Path = _DEBUG_DIR) -> str:
    """Read artifacts from debug_dir and return a Markdown report string."""
    data = {key: _load(debug_dir, key) for key in _ARTIFACT_FILES}

    parts = ["# Latest Recommendation Debug Report\n"]
    parts.append(_section("Replay / Round", _section_replay_round(data["state_view"])))
    parts.append(
        _section(
            "Coordinate Frame", _section_coordinate_frame(data["coordinate_frame"])
        )
    )
    parts.append(_section("Main Threats", _section_threats(data["features"])))
    parts.append(
        _section("Legal Actions", _section_legal_actions(data["legal_actions"]))
    )
    parts.append(_section("Tactical Bundles", _section_bundles(data["bundles"])))
    parts.append(
        _section(
            "Influence Analysis",
            _section_influence(data.get("influence_findings"), data.get("plan_scores")),
        )
    )
    parts.append(_section("Planner Plans", _section_plans(data["plans"])))
    parts.append(_section("Validation Errors", _section_validation(data["validation"])))
    parts.append(
        _section(
            "Resolved Placement",
            _section_resolved_placement(data["resolved_placement"]),
        )
    )
    parts.append(_section("Plan Scores", _section_plan_scores(data["plan_scores"])))
    parts.append(_section("Judge Selection", _section_judge(data["judge"])))
    parts.append(
        _section(
            "Final Recommendation", _section_recommendation(data["recommendation"])
        )
    )
    parts.append(_section("Stage Timings", _section_timings(data["timings"])))
    parts.append(_section("Suspected Failure Stage", _suspect_failure_stage(data)))

    return "".join(parts)


def save_report(debug_dir: Path = _DEBUG_DIR) -> Path:
    """Write the debug report to latest_failure_report.md and return the path."""
    report = build_report(debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)
    out = debug_dir / "latest_failure_report.md"
    out.write_text(report, encoding="utf-8")
    return out
