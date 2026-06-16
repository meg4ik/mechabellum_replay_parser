from __future__ import annotations

from .schemas import (
    CandidatePlan,
    CoachRecommendation,
    JudgeOutput,
    PlanValidationResult,
    ResolvedPlacement,
    StateView,
    TacticalFeatures,
)


def _format_placement_line(p: dict) -> str:
    unit = p.get("unit", "?")
    action = p.get("action", "keep")
    x, y = p.get("x"), p.get("y")
    lane, depth = p.get("lane"), p.get("depth")
    loc = f"({x}, {y})"
    if lane and depth:
        loc += f" {lane}_{depth}"
    return f"  {unit} -> {loc} [{action}]"


def _format_coach_text(
    judge: JudgeOutput,
    plan: CandidatePlan | None,
    state: StateView,
    features: TacticalFeatures,
    final_placement: list[dict] | None = None,
) -> str:
    lines: list[str] = [
        f"Round {state.round} plan for {state.player_name}",
        f"Tempo: {features.tempo_state}  |  Posture: {features.board_posture}",
        "",
    ]

    if plan:
        lines += [
            f"** {plan.title} **",
            f"Goal: {plan.main_goal}",
            f"Why: {plan.why_it_works}",
            "",
        ]

    lines += [
        f"Decision: {judge.main_reason}",
        "",
    ]

    effective_placement = (
        final_placement if final_placement is not None else judge.placement
    )
    if effective_placement:
        lines.append("Placement:")
        for p in effective_placement:
            lines.append(_format_placement_line(p))
        lines.append("")

    if features.threats:
        lines.append("Threats addressed:")
        for t in features.threats:
            lines.append(f"  [{t.severity:.0%}] {t.key} — answer: {t.my_answer}")
        lines.append("")

    if judge.watch_next_round:
        lines.append("Watch next round:")
        for obs in judge.watch_next_round:
            lines.append(f"  - {obs}")
        lines.append("")

    if judge.mistake_to_avoid:
        lines.append(f"Mistake to avoid: {judge.mistake_to_avoid}")

    if plan and plan.risks:
        lines.append("Risks: " + "; ".join(plan.risks))

    return "\n".join(lines)


class RecommendationBuilder:
    def build(
        self,
        judge: JudgeOutput,
        validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
        features: TacticalFeatures,
        state: StateView,
        validation: PlanValidationResult | None = None,
        resolved_placements: list[ResolvedPlacement] | None = None,
    ) -> CoachRecommendation:
        selected_plan = next(
            (p for p, _ in validated_plans if p.id == judge.best_plan_id),
            validated_plans[0][0] if validated_plans else None,
        )

        selected_validation = next(
            (r for p, r in validated_plans if p.id == judge.best_plan_id),
            validated_plans[0][1] if validated_plans else None,
        )

        if resolved_placements:
            placement_dicts = [r.model_dump() for r in resolved_placements]
        else:
            placement_dicts = selected_plan.placement if selected_plan else []

        coach_text = _format_coach_text(
            judge, selected_plan, state, features, final_placement=placement_dicts
        )
        main_threats = [t.key for t in features.threats if t.severity >= 0.5]

        return CoachRecommendation(
            summary=judge.main_reason,
            confidence=judge.confidence,
            main_threats=main_threats,
            placement=placement_dicts,
            resolved_placements=resolved_placements or [],
            risks=(selected_plan.risks if selected_plan else features.my_weaknesses),
            watch_next_round=judge.watch_next_round,
            coach_text=coach_text,
            validation=selected_validation or validation,
        )
