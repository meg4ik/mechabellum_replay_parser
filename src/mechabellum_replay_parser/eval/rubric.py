from __future__ import annotations

from pydantic import BaseModel

from ..coach.influence_schemas import InfluenceAnalysisSummary
from ..coach.schemas import (
    CandidatePlan,
    PlanScoreBreakdown,
    PlanValidationResult,
    TacticalBundle,
    TacticalFeatures,
)
from .cases import EvalCase


class RubricScores(BaseModel):
    legality: int  # 0 or 1
    main_threat_answered: int  # 0..5
    supply_efficiency: int  # 0..5
    positioning: int  # 0..5
    next_round_flexibility: int  # 0..5
    explanation_quality: int  # 0..5 (always 3 in automated eval)
    total: float
    notes: list[str] = []

    influence_finding_accuracy: float = 0.0
    influence_zone_accuracy: float = 0.0
    influence_plan_improvement: float = 0.0


_MAX_TOTAL = 30.0  # 6 × 5


class EvalRubric:
    def score_case(
        self,
        case: EvalCase,
        features: TacticalFeatures,
        bundles: list[TacticalBundle],
        score_breakdowns: list[PlanScoreBreakdown],
        validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
        influence: InfluenceAnalysisSummary | None = None,
    ) -> RubricScores:
        notes: list[str] = []

        # ── legality ──────────────────────────────────────────────────────────
        legality = 1 if any(r.is_valid for _, r in validated_plans) else 0
        if not legality:
            notes.append("No valid synthetic plans were generated.")

        # ── main_threat_answered ──────────────────────────────────────────────
        feature_keys = {t.key for t in features.threats}
        must = set(case.expected.must_address_threats)
        if must:
            matched = must & feature_keys
            main_threat_answered = min(5, int(5 * len(matched) / len(must)))
            if must - matched:
                notes.append(f"Threats not detected: {sorted(must - matched)}")
        else:
            main_threat_answered = 5  # no specific threats required

        # ── remaining dimensions from best plan's PlanScorer scores ───────────
        best = (
            max(score_breakdowns, key=lambda s: s.total_score)
            if score_breakdowns
            else None
        )
        supply_efficiency = int((best.supply_efficiency * 5)) if best else 0
        positioning = int((best.positioning_safety * 5)) if best else 0
        next_round_flexibility = int((best.flexibility_next_round * 5)) if best else 0

        # ── explanation_quality — not automatable ─────────────────────────────
        explanation_quality = 3

        total = float(
            legality * 5
            + main_threat_answered
            + supply_efficiency
            + positioning
            + next_round_flexibility
            + explanation_quality
        )

        inf_finding_acc, inf_zone_acc, inf_plan_imp = self._score_influence(
            case,
            influence,
            score_breakdowns,
            notes,
        )

        return RubricScores(
            legality=legality,
            main_threat_answered=main_threat_answered,
            supply_efficiency=supply_efficiency,
            positioning=positioning,
            next_round_flexibility=next_round_flexibility,
            explanation_quality=explanation_quality,
            total=round(total, 2),
            notes=notes,
            influence_finding_accuracy=inf_finding_acc,
            influence_zone_accuracy=inf_zone_acc,
            influence_plan_improvement=inf_plan_imp,
        )

    def _score_influence(
        self,
        case: EvalCase,
        influence: InfluenceAnalysisSummary | None,
        score_breakdowns: list[PlanScoreBreakdown],
        notes: list[str],
    ) -> tuple[float, float, float]:
        if not influence:
            return 0.0, 0.0, 0.0

        expected_findings = set(case.expected.expected_influence_findings)
        expected_zones = set(case.expected.expected_critical_zones)
        forbidden_findings = set(case.expected.forbidden_high_severity_findings)

        found_keys = {f.key for f in influence.tactical_findings}

        if expected_findings:
            matched = expected_findings & found_keys
            finding_acc = len(matched) / len(expected_findings)
            missing = expected_findings - found_keys
            if missing:
                notes.append(f"Missing influence findings: {sorted(missing)}")
        else:
            finding_acc = 1.0

        for ff in forbidden_findings:
            high_sev = [
                f
                for f in influence.tactical_findings
                if f.key == ff and f.severity >= 0.5
            ]
            if high_sev:
                notes.append(f"Forbidden high-severity finding present: {ff}")
                finding_acc = max(0.0, finding_acc - 0.3)

        if expected_zones:
            critical_zone_ids = {z.zone.value for z in influence.critical_zones}
            zone_matched = expected_zones & critical_zone_ids
            zone_acc = len(zone_matched) / len(expected_zones)
            missing_zones = expected_zones - critical_zone_ids
            if missing_zones:
                notes.append(f"Missing critical zones: {sorted(missing_zones)}")
        else:
            zone_acc = 1.0

        best = (
            max(score_breakdowns, key=lambda s: s.total_score)
            if score_breakdowns
            else None
        )
        plan_imp = best.influence_improvement if best else 0.0

        return round(finding_acc, 3), round(zone_acc, 3), round(plan_imp, 3)
