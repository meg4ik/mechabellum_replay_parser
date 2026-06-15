from __future__ import annotations

import asyncio

from .feature_extractor import FeatureExtractor
from .schemas import CoachRecommendation
from .state_view import StateViewBuilder


class CoachEngine:
    """Orchestrates the coaching pipeline.

    Phase 4: StateViewBuilder + FeatureExtractor are wired in; the LLM call
    still goes through the legacy llm.analyze() (runs in a thread pool).
    Phase 6 will replace that with Planner → Validator → Judge.
    """

    def __init__(self) -> None:
        self._state_view_builder = StateViewBuilder()
        self._feature_extractor = FeatureExtractor()

    async def analyze_replay(
        self,
        parsed: dict,
        supply: int | None,
        player_name: str,
    ) -> CoachRecommendation:
        state = self._state_view_builder.build(parsed, supply, player_name)
        features = self._feature_extractor.extract(state)

        # Legacy LLM call — blocking, runs in a thread pool.
        from ..llm import analyze as _legacy_analyze

        coach_text = ""
        placement: list[dict] = []
        try:
            result = await asyncio.to_thread(_legacy_analyze, parsed, supply=supply)
            placement = result or []
        except Exception as exc:
            coach_text = f"[LLM error] {exc}"

        main_threats = [t.key for t in features.threats if t.severity >= 0.5]

        return CoachRecommendation(
            summary=(
                f"Round {state.round} — {player_name} | "
                f"tempo={features.tempo_state}, "
                f"posture={features.board_posture}"
            ),
            main_threats=main_threats,
            placement=placement,
            risks=features.my_weaknesses,
            watch_next_round=features.likely_enemy_continuation,
            coach_text=coach_text,
        )
