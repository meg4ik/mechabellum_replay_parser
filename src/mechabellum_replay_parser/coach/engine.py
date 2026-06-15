from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..knowledge.parser import parse_knowledge_file
from ..knowledge.retriever import KnowledgeRetriever
from ..llm.client import LLMProvider
from ..llm.providers.openai_provider import OpenAIProvider
from .feature_extractor import FeatureExtractor
from .judge import Judge
from .legal_actions import LegalActionGenerator
from .planner import Planner
from .recommendation_builder import RecommendationBuilder
from .schemas import CandidatePlan, CoachRecommendation, JudgeOutput, PlanValidationResult
from .state_view import StateViewBuilder
from .validator import PlanValidator


@dataclass
class CoachAnalysis:
    """Full pipeline result — recommendation plus all intermediate data for persistence."""

    recommendation: CoachRecommendation
    validated_plans: list[tuple[CandidatePlan, PlanValidationResult]] = field(default_factory=list)
    judge_output: JudgeOutput | None = None
    model_name: str | None = None

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
# game_knowledge.md lives two levels above the src/ tree root
_DEFAULT_KNOWLEDGE_FILE = Path(__file__).parent.parent.parent.parent / "game_knowledge.md"


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
        return (await self.analyze_replay_detailed(parsed, supply, player_name)).recommendation

    async def analyze_replay_detailed(
        self,
        parsed: dict,
        supply: int | None,
        player_name: str,
    ) -> CoachAnalysis:
        state = self._state_view_builder.build(parsed, supply, player_name)
        features = self._feature_extractor.extract(state)
        legal_actions, action_groups = self._legal_action_generator.generate(state, features)

        knowledge_chunks = self._retriever.retrieve(state, features)

        plans = await self._planner.generate_plans(
            state, features, action_groups, knowledge_chunks
        )

        validated_plans = [
            (plan, self._plan_validator.validate_placement(plan.placement, state, legal_actions))
            for plan in plans
        ]

        judge_output = await self._judge.select_plan(
            state, features, validated_plans, knowledge_chunks
        )

        recommendation = self._recommendation_builder.build(
            judge_output, validated_plans, features, state
        )

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        return CoachAnalysis(
            recommendation=recommendation,
            validated_plans=validated_plans,
            judge_output=judge_output,
            model_name=model_name,
        )

    def build_state_view(self, parsed: dict, supply: int | None, player_name: str):
        """Expose StateViewBuilder for external callers."""
        return self._state_view_builder.build(parsed, supply, player_name)
