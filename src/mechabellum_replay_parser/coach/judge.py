from __future__ import annotations

import json
import logging

from ..llm.client import LLMProvider
from .schemas import (
    CandidatePlan,
    JudgeOutput,
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
) -> str:
    plans_data = []
    for plan, result in validated_plans:
        plans_data.append({
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
        })

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
) -> JudgeOutput:
    """Select the first valid plan, or the fallback plan, without LLM."""
    for plan, result in validated_plans:
        if result.is_valid:
            return JudgeOutput(
                best_plan_id=plan.id,
                confidence=plan.confidence,
                main_reason="Selected automatically: first valid plan (Judge LLM unavailable).",
                placement=plan.placement,
                watch_next_round=[],
                mistake_to_avoid="",
            )
    # No valid plan — still return the first one
    if validated_plans:
        plan, _ = validated_plans[0]
        return JudgeOutput(
            best_plan_id=plan.id,
            confidence=0.1,
            main_reason="No valid plans available — using fallback.",
            placement=plan.placement,
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
    ) -> JudgeOutput:
        user = _build_user(state, features, validated_plans, knowledge_chunks or [])

        try:
            raw = await self._provider.complete_json(
                system=self._system,
                user=user,
                temperature=0.15,
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning("Judge LLM call failed: %s", exc)
            return _make_fallback_judge_output(validated_plans)

        try:
            return JudgeOutput.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            _log.warning("Judge returned invalid JSON shape: %s", exc)
            return _make_fallback_judge_output(validated_plans)
