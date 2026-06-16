from __future__ import annotations

import json
import logging

from ..llm.client import LLMProvider
from .schemas import (
    CandidatePlan,
    JudgeOutput,
    PlanScoreBreakdown,
    PlanValidationResult,
    StateView,
    TacticalFeatures,
)

_log = logging.getLogger(__name__)

PROMPT_VERSION = "judge_v1"


def _build_user(
    state: StateView,
    features: TacticalFeatures,
    validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
    knowledge_chunks: list[str],
    score_breakdowns: list[PlanScoreBreakdown] | None = None,
) -> str:
    score_map = {s.plan_id: s for s in (score_breakdowns or [])}
    plans_data = []
    for plan, result in validated_plans:
        entry: dict = {
            "id": plan.id,
            "title": plan.title,
            "total_cost": plan.total_cost,
            "main_goal": plan.main_goal,
            "why_it_works": plan.why_it_works,
            "risks": plan.risks,
            "expected_enemy_response": plan.expected_enemy_response,
            "confidence": plan.confidence,
            "placement": plan.placement,
            "validation": {
                "is_valid": result.is_valid,
                "issues": [
                    {"severity": i.severity, "code": i.code, "message": i.message}
                    for i in result.issues
                ],
            },
        }
        if plan.id in score_map:
            s = score_map[plan.id]
            entry["score"] = {
                "total": s.total_score,
                "threat_coverage": s.threat_coverage,
                "supply_efficiency": s.supply_efficiency,
                "tempo": s.tempo,
                "tower_protection": s.tower_protection,
                "warnings": s.warnings,
            }
        plans_data.append(entry)

    data: dict = {
        "round": state.round,
        "player": state.player_name,
        "supply": state.my_supply,
        "tempo": features.tempo_state,
        "posture": features.board_posture,
        "threats": [
            {"key": t.key, "severity": round(t.severity, 2), "my_answer": t.my_answer}
            for t in features.threats
        ],
        "strategic_memory": {
            "do_not_forget": state.strategic_memory.do_not_forget,
        },
        "candidate_plans": plans_data,
    }
    if knowledge_chunks:
        data["relevant_knowledge"] = knowledge_chunks
    return json.dumps(data, ensure_ascii=False, indent=2)


def _make_fallback_judge_output(
    validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
    score_breakdowns: list[PlanScoreBreakdown] | None = None,
) -> JudgeOutput:
    """Select the highest-scoring valid plan without LLM. Judge never owns placement."""
    score_map = {s.plan_id: s.total_score for s in (score_breakdowns or [])}
    valid_plans = [(p, r) for p, r in validated_plans if r.is_valid]
    if valid_plans:
        best_plan, _ = max(
            valid_plans,
            key=lambda pr: score_map.get(pr[0].id, pr[0].confidence),
        )
        return JudgeOutput(
            best_plan_id=best_plan.id,
            confidence=best_plan.confidence,
            main_reason="Selected automatically: highest-scoring valid plan (Judge LLM unavailable).",
            placement=[],
            watch_next_round=[],
            mistake_to_avoid="",
        )
    if validated_plans:
        plan, _ = validated_plans[0]
        return JudgeOutput(
            best_plan_id=plan.id,
            confidence=0.1,
            main_reason="No valid plans available — using fallback.",
            placement=[],
            watch_next_round=[],
            mistake_to_avoid="",
        )
    return JudgeOutput(
        best_plan_id="plan_fallback",
        confidence=0.0,
        main_reason="No plans available.",
        placement=[],
        watch_next_round=[],
        mistake_to_avoid="",
    )


class Judge:
    def __init__(self, provider: LLMProvider, system_prompt: str) -> None:
        self._provider = provider
        self._system = system_prompt

    async def select_plan(
        self,
        state: StateView,
        features: TacticalFeatures,
        validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
        knowledge_chunks: list[str] | None = None,
        score_breakdowns: list[PlanScoreBreakdown] | None = None,
    ) -> JudgeOutput:
        user = _build_user(
            state, features, validated_plans, knowledge_chunks or [], score_breakdowns
        )

        try:
            raw = await self._provider.complete_json(
                system=self._system,
                user=user,
                temperature=0.15,
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning("Judge LLM call failed: %s", exc)
            return _make_fallback_judge_output(validated_plans, score_breakdowns)

        try:
            output = JudgeOutput.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            _log.warning("Judge returned invalid JSON shape: %s", exc)
            return _make_fallback_judge_output(validated_plans, score_breakdowns)

        # ── LLM contract enforcement ───────────────────────────────────────────
        # Judge must not own placement — strip it regardless.
        output = output.model_copy(update={"placement": []})

        # Judge must not select an invalid plan.
        invalid_ids = {p.id for p, r in validated_plans if not r.is_valid}
        if output.best_plan_id in invalid_ids:
            _log.warning(
                "Judge selected invalid plan %s — falling back",
                output.best_plan_id,
            )
            return _make_fallback_judge_output(validated_plans, score_breakdowns)

        return output
