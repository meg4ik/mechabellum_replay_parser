from __future__ import annotations

from pydantic import BaseModel

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


_MAX_TOTAL = 30.0  # 6 × 5


class EvalRubric:
    def score_case(
        self,
        case: EvalCase,
        features: TacticalFeatures,
        bundles: list[TacticalBundle],
        score_breakdowns: list[PlanScoreBreakdown],
        validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
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

        return RubricScores(
            legality=legality,
            main_threat_answered=main_threat_answered,
            supply_efficiency=supply_efficiency,
            positioning=positioning,
            next_round_flexibility=next_round_flexibility,
            explanation_quality=explanation_quality,
            total=round(total, 2),
            notes=notes,
        )
