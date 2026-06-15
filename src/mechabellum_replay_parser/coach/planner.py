from __future__ import annotations

import json
import logging

from ..llm.client import LLMProvider
from .schemas import (
    ActionGroup,
    CandidatePlan,
    StateView,
    TacticalFeatures,
)

_log = logging.getLogger(__name__)

PROMPT_VERSION = "planner_v1"


def _compact_state(
    state: StateView,
    features: TacticalFeatures,
    action_groups: list[ActionGroup],
    knowledge_chunks: list[str],
) -> str:
    data: dict = {
        "round": state.round,
        "player": state.player_name,
        "supply": state.my_supply,
        "buys_remaining": state.my_state.shop.buys_remaining if state.my_state.shop else None,
        "unlocks_remaining": state.my_state.shop.unlocks_remaining if state.my_state.shop else None,
        "my_army_value": state.my_state.army_value,
        "enemy_army_value": sum(es.army_value or 0 for es in state.enemy_states),
        "tempo": features.tempo_state,
        "posture": features.board_posture,
        "threats": [
            {
                "key": t.key,
                "severity": round(t.severity, 2),
                "source_units": t.source_units,
                "my_answer": t.my_answer,
                "explanation": t.explanation,
            }
            for t in features.threats
        ],
        "my_units": [
            {
                "name": u.name,
                "x": u.position.x if u.position else None,
                "y": u.position.y if u.position else None,
                "active_techs": u.active_techs,
            }
            for u in state.my_state.units
        ],
        "enemy_units": [
            {"name": u.name}
            for es in state.enemy_states
            for u in es.units
        ],
        "my_constructions": [
            {
                "type": c.type,
                "x": c.position.x if c.position else None,
                "y": c.position.y if c.position else None,
            }
            for c in state.my_state.constructions
        ],
        "strategic_memory": {
            "critical_events": state.strategic_memory.critical_events,
            "do_not_forget": state.strategic_memory.do_not_forget,
        },
        "action_groups": [
            {
                "id": g.id,
                "title": g.title,
                "purpose": g.purpose,
                "addresses_threats": g.addresses_threats,
                "total_cost": g.total_cost,
                "actions": [
                    {
                        "id": a.id,
                        "type": a.type,
                        "unit": a.unit,
                        "cost": a.cost,
                        "tags": a.reason_tags,
                    }
                    for a in g.actions
                ],
            }
            for g in action_groups
        ],
    }
    if knowledge_chunks:
        data["relevant_knowledge"] = knowledge_chunks
    return json.dumps(data, ensure_ascii=False, indent=2)


def _make_fallback_plan(state: StateView) -> CandidatePlan:
    """Keep-all plan used when the LLM planner fails."""
    placement = [
        {
            "unit": u.name,
            "x": u.position.x if u.position else 0,
            "y": u.position.y if u.position else -100,
            "action": "keep",
        }
        for u in state.my_state.units
        if u.position
    ]
    return CandidatePlan(
        id="plan_fallback",
        title="Hold position (fallback)",
        action_ids=[f"keep_{u.name}_{u.index or 0}" for u in state.my_state.units],
        total_cost=0,
        main_goal="Maintain current army — Planner LLM did not respond.",
        why_it_works="Safe default: no supply spent, all units kept in position.",
        risks=["No adaptation this round."],
        expected_enemy_response=["Enemy continues their strategy."],
        placement=placement,
        confidence=0.1,
    )


class Planner:
    def __init__(self, provider: LLMProvider, system_prompt: str) -> None:
        self._provider = provider
        self._system = system_prompt

    async def generate_plans(
        self,
        state: StateView,
        features: TacticalFeatures,
        action_groups: list[ActionGroup],
        knowledge_chunks: list[str] | None = None,
    ) -> list[CandidatePlan]:
        user = _compact_state(state, features, action_groups, knowledge_chunks or [])

        try:
            raw = await self._provider.complete_json(
                system=self._system,
                user=user,
                temperature=0.4,
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning("Planner LLM call failed: %s", exc)
            return [_make_fallback_plan(state)]

        plans_raw = raw.get("plans", [])
        if not isinstance(plans_raw, list):
            _log.warning("Planner returned non-list plans value (%s) — using fallback", type(plans_raw).__name__)
            return [_make_fallback_plan(state)]

        plans: list[CandidatePlan] = []
        for raw_plan in plans_raw:
            try:
                plans.append(CandidatePlan.model_validate(raw_plan))
            except Exception as exc:  # noqa: BLE001
                plan_id = raw_plan.get("id") if isinstance(raw_plan, dict) else repr(raw_plan)
                _log.debug("Skipping invalid plan from LLM: %s — %s", plan_id, exc)

        if not plans:
            _log.warning("Planner returned 0 valid plans — using fallback")
            plans = [_make_fallback_plan(state)]

        return plans
