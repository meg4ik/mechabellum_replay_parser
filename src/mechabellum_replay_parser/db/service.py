"""PersistenceService: single facade for all DB writes.

Set DEBUG_NO_DB=true (or pass session_factory=None) for a no-op mode that
lets the app run without a database connection.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .repositories import FeedbackRepository, RecommendationRepository

if TYPE_CHECKING:
    from ..coach.engine import CoachAnalysis


class PersistenceService:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession] | None
    ) -> None:
        self._factory = session_factory

    @property
    def enabled(self) -> bool:
        return self._factory is not None

    # ── match + recommendation ────────────────────────────────────────────────

    async def save_match_analysis(
        self,
        *,
        rec_id: str,
        source_file: str,
        parsed: dict,
        round_number: int,
        player_name: str,
        supply: int | None,
        analysis: CoachAnalysis,
    ) -> None:
        if not self.enabled:
            return

        assert self._factory is not None
        async with self._factory() as session:
            async with session.begin():
                repo = RecommendationRepository(session)

                meta = parsed.get("metadata", {})
                teams = parsed.get("teams", [])
                rounds_list = parsed.get("rounds", [])
                raw_round = next(
                    (r for r in rounds_list if r.get("round") == round_number),
                    rounds_list[-1] if rounds_list else None,
                )

                match_row = await repo.create_match(
                    source_file=source_file,
                    match_mode=meta.get("match_mode"),
                    player_name=player_name,
                    teams=teams,
                )

                round_row = await repo.create_round(
                    match_id=match_row.id,
                    round_number=round_number,
                    raw_round=raw_round,
                )

                await repo.create_recommendation(
                    rec_id=rec_id,
                    match_id=match_row.id,
                    round_id=round_row.id,
                    round_number=round_number,
                    player_name=player_name,
                    model_name=analysis.model_name,
                )

                await repo.mark_completed(
                    rec_id=rec_id,
                    recommendation=analysis.recommendation,
                    supply=supply,
                )

                selected_id = (
                    analysis.judge_output.best_plan_id
                    if analysis.judge_output
                    else None
                )
                await repo.save_candidate_plans(
                    rec_id=rec_id,
                    validated_plans=analysis.validated_plans,
                    selected_plan_id=selected_id,
                )

                llm_calls = [
                    {"stage": "planner", "model": analysis.model_name},
                    {"stage": "judge", "model": analysis.model_name},
                ]
                await repo.save_llm_calls(rec_id=rec_id, calls=llm_calls)

    # ── feedback ─────────────────────────────────────────────────────────────

    async def save_feedback(
        self,
        recommendation_id: str,
        rating: int | None = None,
        label: str | None = None,
        comment: str | None = None,
        followed_plan: bool | None = None,
    ) -> None:
        if not self.enabled:
            return

        assert self._factory is not None
        async with self._factory() as session:
            repo = FeedbackRepository(session)
            await repo.save_feedback(
                recommendation_id=recommendation_id,
                rating=rating,
                label=label,
                comment=comment,
                followed_plan=followed_plan,
            )


def create_persistence_service() -> PersistenceService:
    """Build PersistenceService from environment.

    Returns a no-op service when DEBUG_NO_DB=true.
    """
    if os.getenv("DEBUG_NO_DB", "").lower() in ("1", "true", "yes"):
        print("[db] DEBUG_NO_DB=true — persistence disabled")
        return PersistenceService(None)

    try:
        from .session import get_session_factory

        factory = get_session_factory()
        return PersistenceService(factory)
    except Exception as exc:
        print(f"[db] Cannot initialise DB engine (non-fatal): {exc}")
        return PersistenceService(None)
