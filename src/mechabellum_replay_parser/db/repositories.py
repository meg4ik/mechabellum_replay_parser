from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    CandidatePlanRow,
    Feedback,
    LLMCall,
    Match,
    OutcomeSnapshot,
    Recommendation,
    Round,
)

if TYPE_CHECKING:
    from ..coach.schemas import CandidatePlan, CoachRecommendation, PlanValidationResult


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_match(
        self,
        source_file: str | None,
        match_mode: str | None,
        player_name: str | None,
        teams: object,
    ) -> Match:
        row = Match(
            source_file=source_file,
            match_mode=match_mode,
            player_name=player_name,
            teams=teams,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def create_round(
        self,
        match_id: str,
        round_number: int,
        raw_round: dict | None = None,
        state_view: dict | None = None,
        features: dict | None = None,
    ) -> Round:
        row = Round(
            match_id=match_id,
            round_number=round_number,
            raw_round=raw_round,
            state_view=state_view,
            features=features,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def create_recommendation(
        self,
        rec_id: str,
        match_id: str | None,
        round_id: str | None,
        round_number: int,
        player_name: str | None,
        model_name: str | None = None,
    ) -> Recommendation:
        row = Recommendation(
            id=rec_id,
            match_id=match_id,
            round_id=round_id,
            round_number=round_number,
            player_name=player_name,
            model_name=model_name,
            status="created",
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def mark_completed(
        self,
        rec_id: str,
        recommendation: CoachRecommendation,
        supply: int | None,
        influence_summary_json: dict | None = None,
        influence_findings_json: list | None = None,
    ) -> None:
        row = await self._session.get(Recommendation, rec_id)
        if row is None:
            return
        row.status = "completed"
        row.supply = supply
        row.final_summary = recommendation.summary
        row.final_recommendation = recommendation.model_dump(mode="json")
        row.placement = recommendation.placement
        row.confidence = recommendation.confidence
        row.influence_summary_json = influence_summary_json
        row.influence_findings_json = influence_findings_json
        row.completed_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def mark_failed(self, rec_id: str) -> None:
        row = await self._session.get(Recommendation, rec_id)
        if row is None:
            return
        row.status = "failed"
        row.completed_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def save_candidate_plans(
        self,
        rec_id: str,
        validated_plans: list[tuple[CandidatePlan, PlanValidationResult]],
        selected_plan_id: str | None,
        score_breakdowns: list | None = None,
    ) -> None:
        score_map: dict[str, dict] = {}
        if score_breakdowns:
            for s in score_breakdowns:
                s_dict = s if isinstance(s, dict) else s.model_dump(mode="json")
                score_map[s_dict.get("plan_id", "")] = s_dict

        for plan, validation in validated_plans:
            score_data = score_map.get(plan.id)
            influence_delta = None
            if score_data and score_data.get("influence_improvement"):
                influence_delta = {
                    "influence_improvement": score_data.get("influence_improvement", 0),
                    "anti_air_improvement": score_data.get("anti_air_improvement", 0),
                    "anti_chaff_improvement": score_data.get(
                        "anti_chaff_improvement", 0
                    ),
                    "anti_heavy_improvement": score_data.get(
                        "anti_heavy_improvement", 0
                    ),
                    "artillery_risk_reduction": score_data.get(
                        "artillery_risk_reduction", 0
                    ),
                    "influence_explanation": score_data.get(
                        "influence_explanation", []
                    ),
                }
            cp = CandidatePlanRow(
                recommendation_id=rec_id,
                plan_key=plan.id,
                planner_output=plan.model_dump(mode="json"),
                validation_result=validation.model_dump(mode="json"),
                is_selected=(plan.id == selected_plan_id),
                plan_score_json=score_data,
                influence_delta_json=influence_delta,
            )
            self._session.add(cp)
        await self._session.flush()

    async def save_llm_calls(
        self,
        rec_id: str,
        calls: list[dict],
    ) -> None:
        now = datetime.now(timezone.utc)
        for call in calls:
            lc = LLMCall(
                recommendation_id=rec_id,
                stage=call.get("stage"),
                provider=call.get("provider"),
                model=call.get("model"),
                prompt_version=call.get("prompt_version"),
                completed_at=now,
            )
            self._session.add(lc)
        await self._session.flush()


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_feedback(
        self,
        recommendation_id: str,
        rating: int | None = None,
        label: str | None = None,
        comment: str | None = None,
        followed_plan: bool | None = None,
    ) -> Feedback:
        row = Feedback(
            recommendation_id=recommendation_id,
            rating=rating,
            label=label,
            comment=comment,
            followed_plan=followed_plan,
        )
        self._session.add(row)
        await self._session.commit()
        return row


class OutcomeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_outcome_snapshot(
        self,
        recommendation_id: str,
        next_round_number: int,
        *,
        before_hp: int | None = None,
        next_round_hp: int | None = None,
        hp_delta: int | None = None,
        fight_outcome_next_round: str | None = None,
        units_survived_next_round: int | None = None,
        enemy_units_survived_next_round: int | None = None,
        tower_lost_next_round: bool | None = None,
        player_followed_plan: bool | None = None,
        notes: str | None = None,
        next_round_state: dict | None = None,
    ) -> OutcomeSnapshot:
        row = OutcomeSnapshot(
            recommendation_id=recommendation_id,
            next_round_number=next_round_number,
            before_hp=before_hp,
            next_round_hp=next_round_hp,
            hp_delta=hp_delta,
            fight_outcome_next_round=fight_outcome_next_round,
            units_survived_next_round=units_survived_next_round,
            enemy_units_survived_next_round=enemy_units_survived_next_round,
            tower_lost_next_round=tower_lost_next_round,
            player_followed_plan=player_followed_plan,
            notes=notes,
            next_round_state=next_round_state,
        )
        self._session.add(row)
        await self._session.flush()
        return row
