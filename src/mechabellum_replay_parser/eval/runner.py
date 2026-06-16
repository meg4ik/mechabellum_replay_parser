from __future__ import annotations

from pydantic import BaseModel

from ..coach.feature_extractor import FeatureExtractor
from ..coach.legal_actions import LegalActionGenerator
from ..coach.plan_scorer import PlanScorer
from ..coach.schemas import (
    CandidatePlan,
    LegalAction,
    TacticalBundle,
)
from ..coach.tactical_bundles import TacticalBundleGenerator
from ..coach.validator import PlanValidator
from .cases import EvalCase
from .rubric import EvalRubric, RubricScores

_PASS_MIN_THREAT = 3


class EvalResult(BaseModel):
    case_name: str
    scores: RubricScores
    passed: bool
    threat_keys_found: list[str]
    bundle_themes_found: list[str]
    best_plan_score: float | None = None


class EvalRunner:
    def __init__(self) -> None:
        self._feature_extractor = FeatureExtractor()
        self._legal_gen = LegalActionGenerator()
        self._bundle_gen = TacticalBundleGenerator()
        self._plan_scorer = PlanScorer()
        self._validator = PlanValidator()
        self._rubric = EvalRubric()

    def run_case(self, case: EvalCase) -> EvalResult:
        # Re-run deterministic pipeline (no LLM required)
        features = self._feature_extractor.extract(case.state_view)
        legal_actions, action_groups = self._legal_gen.generate(
            case.state_view, features
        )
        bundles = self._bundle_gen.generate(case.state_view, features, legal_actions)

        # Build one synthetic plan per bundle for scoring
        plans = _build_plans(bundles, legal_actions)
        validated = [
            (
                plan,
                self._validator.validate_placement(
                    plan.placement, case.state_view, legal_actions
                ),
            )
            for plan in plans
        ]
        score_breakdowns = self._plan_scorer.score_all(
            validated, features, case.state_view
        )

        rubric_scores = self._rubric.score_case(
            case, features, bundles, score_breakdowns, validated
        )

        passed = (
            rubric_scores.legality == 1
            and rubric_scores.main_threat_answered >= _PASS_MIN_THREAT
        )
        best = (
            max(score_breakdowns, key=lambda s: s.total_score)
            if score_breakdowns
            else None
        )
        return EvalResult(
            case_name=case.name,
            scores=rubric_scores,
            passed=passed,
            threat_keys_found=[t.key for t in features.threats],
            bundle_themes_found=[b.theme for b in bundles],
            best_plan_score=best.total_score if best else None,
        )

    def run_all(self, cases: list[EvalCase]) -> list[EvalResult]:
        return [self.run_case(c) for c in cases]


def _build_plans(
    bundles: list[TacticalBundle],
    legal_actions: list[LegalAction],
) -> list[CandidatePlan]:
    """Build one synthetic CandidatePlan per tactical bundle for scoring."""
    plans: list[CandidatePlan] = []
    cost_map = {a.id: a.cost for a in legal_actions}

    for bundle in bundles:
        if not bundle.required_action_ids:
            continue
        # Compute actual cost from legal_actions if possible
        cost = sum(
            cost_map.get(aid, 0)
            for aid in bundle.required_action_ids
            if cost_map.get(aid, 0) > 0
        )
        if cost == 0:
            cost = bundle.estimated_cost

        plans.append(
            CandidatePlan(
                id=f"eval_{bundle.id}",
                title=bundle.title,
                action_ids=bundle.required_action_ids,
                total_cost=cost,
                main_goal=bundle.why_considered,
                why_it_works=bundle.why_considered,
                risks=bundle.risks,
                expected_enemy_response=[],
                placement=[],
                placement_intents=bundle.placement_intents,
                confidence=0.5,
            )
        )

    if not plans:
        plans.append(
            CandidatePlan(
                id="eval_safe_default",
                title="Hold position",
                action_ids=[],
                total_cost=0,
                main_goal="Maintain current army",
                why_it_works="Safe fallback",
                risks=[],
                expected_enemy_response=[],
                placement=[],
                confidence=0.3,
            )
        )
    return plans
