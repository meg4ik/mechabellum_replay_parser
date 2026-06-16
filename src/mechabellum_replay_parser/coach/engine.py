from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..knowledge.parser import parse_knowledge_file
from ..knowledge.retriever import KnowledgeRetriever
from ..llm.client import LLMProvider
from ..llm.providers.openai_provider import OpenAIProvider
from .coordinates import CoordinateFrame
from .feature_extractor import FeatureExtractor
from .judge import Judge, _make_fallback_judge_output
from .legal_actions import LegalActionGenerator
from .placement_resolver import PlacementResolver
from .planner import Planner, _make_fallback_plan
from .recommendation_builder import RecommendationBuilder
from .schemas import (
    CandidatePlan,
    CoachRecommendation,
    JudgeOutput,
    PlanValidationResult,
    StateView,
)
from .state_view import StateViewBuilder
from .validator import PlanValidator

_log = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_DEFAULT_KNOWLEDGE_FILE = (
    Path(__file__).parent.parent.parent.parent / "game_knowledge.md"
)
_DEBUG_DIR = Path(".debug")


@dataclass
class CoachAnalysis:
    """Full pipeline result — recommendation plus all intermediate data for persistence."""

    recommendation: CoachRecommendation
    state_view: StateView | None = None
    validated_plans: list[tuple[CandidatePlan, PlanValidationResult]] = field(
        default_factory=list
    )
    judge_output: JudgeOutput | None = None
    model_name: str | None = None


def _load_prompt(name: str) -> str:
    path = _PROMPTS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are a Mechabellum AI coach. ({name} prompt not found)"


def _load_retriever() -> KnowledgeRetriever:
    kf = Path(os.getenv("MECHABELLUM_KNOWLEDGE_FILE", str(_DEFAULT_KNOWLEDGE_FILE)))
    chunks = parse_knowledge_file(kf) if kf.exists() else []
    return KnowledgeRetriever(chunks)


def _default_provider() -> LLMProvider:
    return OpenAIProvider()


def _is_debug() -> bool:
    return os.getenv("DEBUG", "").lower() in ("1", "true", "yes")


def _write_debug(name: str, data) -> None:
    if not _is_debug():
        return
    try:
        _DEBUG_DIR.mkdir(exist_ok=True)
        path = _DEBUG_DIR / name
        if isinstance(data, str):
            path.write_text(data, encoding="utf-8")
        else:
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
    except Exception as exc:
        _log.debug("Debug artifact write failed for %s: %s", name, exc)


class CoachEngine:
    """Orchestrates the full coaching pipeline.

    StateViewBuilder → FeatureExtractor → LegalActionGenerator
    → KnowledgeRetriever → Planner (LLM) → PlanValidator
    → Judge (LLM) → RecommendationBuilder
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        p = provider or _default_provider()
        self._state_view_builder = StateViewBuilder()
        self._feature_extractor = FeatureExtractor()
        self._legal_action_generator = LegalActionGenerator()
        self._plan_validator = PlanValidator()
        self._placement_resolver = PlacementResolver()
        self._planner = Planner(p, _load_prompt("planner_v1"))
        self._judge = Judge(p, _load_prompt("judge_v1"))
        self._recommendation_builder = RecommendationBuilder()
        self._retriever = _load_retriever()

    async def analyze_replay(
        self,
        parsed: dict,
        supply: int | None,
        player_name: str,
    ) -> CoachRecommendation:
        return (
            await self.analyze_replay_detailed(parsed, supply, player_name)
        ).recommendation

    async def analyze_replay_detailed(
        self,
        parsed: dict,
        supply: int | None,
        player_name: str,
    ) -> CoachAnalysis:
        _start = time.monotonic()
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

        state = self._state_view_builder.build(parsed, supply, player_name)
        _log.info(
            "stage=state_view_built round=%s player=%s supply=%s",
            state.round,
            player_name,
            supply,
        )
        _write_debug("latest_state_view.json", state.model_dump())

        features = self._feature_extractor.extract(state)
        _log.info(
            "stage=features_extracted threats=%d tempo=%s posture=%s",
            len(features.threats),
            features.tempo_state,
            features.board_posture,
        )
        _write_debug("latest_features.json", features.model_dump())

        legal_actions, action_groups = self._legal_action_generator.generate(
            state, features
        )
        _log.info(
            "stage=legal_actions_generated count=%d groups=%d",
            len(legal_actions),
            len(action_groups),
        )
        _write_debug(
            "latest_legal_actions.json", [a.model_dump() for a in legal_actions]
        )

        knowledge_chunks = self._retriever.retrieve(state, features)
        _log.info("stage=knowledge_retrieved chunks=%d", len(knowledge_chunks))

        _log.info("stage=planner_started timeout_s=%s model=%s", timeout, model_name)
        try:
            plans = await asyncio.wait_for(
                self._planner.generate_plans(
                    state, features, action_groups, knowledge_chunks
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            _log.warning(
                "stage=planner_timeout seconds=%s — using fallback plan", timeout
            )
            plans = [_make_fallback_plan(state)]
        _log.info("stage=planner_completed plans=%d", len(plans))
        _write_debug("latest_planner_response.json", [p.model_dump() for p in plans])

        validated_plans = [
            (
                plan,
                self._plan_validator.validate_placement(
                    plan.placement, state, legal_actions
                ),
            )
            for plan in plans
        ]
        valid_count = sum(1 for _, r in validated_plans if r.is_valid)
        _log.info(
            "stage=validation_completed total=%d valid=%d",
            len(validated_plans),
            valid_count,
        )
        _write_debug(
            "latest_validation.json",
            [
                {
                    "plan_id": p.id,
                    "is_valid": r.is_valid,
                    "issues": [i.model_dump() for i in r.issues],
                }
                for p, r in validated_plans
            ],
        )

        try:
            judge_output = await asyncio.wait_for(
                self._judge.select_plan(
                    state, features, validated_plans, knowledge_chunks
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            _log.warning(
                "stage=judge_timeout seconds=%s — picking highest-confidence valid plan",
                timeout,
            )
            judge_output = _make_fallback_judge_output(validated_plans)
        _log.info(
            "stage=judge_completed best_plan_id=%s confidence=%s",
            judge_output.best_plan_id,
            judge_output.confidence,
        )
        _write_debug("latest_judge_response.json", judge_output.model_dump())

        selected_plan = next(
            (p for p, _ in validated_plans if p.id == judge_output.best_plan_id),
            validated_plans[0][0] if validated_plans else None,
        )
        resolved_placements = []
        if selected_plan and selected_plan.placement_intents:
            frame = CoordinateFrame.from_units_and_constructions(
                state.my_state.units, state.my_state.constructions
            )
            resolved_placements = self._placement_resolver.resolve(
                selected_plan.placement_intents, frame, state.my_state.units
            )
            _log.info("stage=placement_resolved count=%d", len(resolved_placements))
        _write_debug(
            "latest_resolved_placement.json",
            [r.model_dump() for r in resolved_placements],
        )

        recommendation = self._recommendation_builder.build(
            judge_output,
            validated_plans,
            features,
            state,
            resolved_placements=resolved_placements or None,
        )
        _log.info(
            "stage=recommendation_ready summary=%r placement_items=%d",
            recommendation.summary,
            len(recommendation.placement or []),
        )
        _write_debug(
            "latest_recommendation.json",
            {
                "summary": recommendation.summary,
                "coach_text": recommendation.coach_text,
                "placement": recommendation.placement,
            },
        )

        elapsed_ms = int((time.monotonic() - _start) * 1000)
        _log.info(
            "pipeline_complete elapsed_ms=%d model=%s",
            elapsed_ms,
            model_name,
        )

        return CoachAnalysis(
            recommendation=recommendation,
            state_view=state,
            validated_plans=validated_plans,
            judge_output=judge_output,
            model_name=model_name,
        )

    def build_state_view(self, parsed: dict, supply: int | None, player_name: str):
        """Expose StateViewBuilder for external callers."""
        return self._state_view_builder.build(parsed, supply, player_name)
