"""JSONL dataset export for recommendation quality training."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db.models import Recommendation

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


_LABEL_PRIORITY: list[tuple[str, str]] = [
    # (feedback_label, derived_label)
    ("bad_illegal", "illegal"),
    ("bad_positioning", "positioning_issue"),
    ("bad_counter", "counter_issue"),
    ("too_expensive", "economy_issue"),
]


class DatasetRow(BaseModel):
    recommendation_id: str
    state_view: dict
    features: dict
    tactical_bundles: list
    candidate_plans: list
    selected_plan: dict | None
    score_breakdowns: list
    influence_summary: dict | None = None
    influence_findings: list | None = None
    plan_influence_deltas: list | None = None
    user_feedback: dict | None = None
    outcome: dict | None = None
    derived_quality_label: str


def derive_quality_label(
    rating: int | None,
    label: str | None,
    hp_delta: int | None,
) -> str:
    # Label-based overrides take precedence over rating
    if label:
        for fb_label, derived in _LABEL_PRIORITY:
            if label == fb_label:
                return derived

    if rating is not None:
        if rating <= 2:
            return "bad"
        if rating >= 4 and (hp_delta is None or hp_delta >= 0):
            return "good"

    return "unknown"


async def export_dataset(
    session_factory: async_sessionmaker[AsyncSession],
    output: Path,
    format: str = "jsonl",
) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(Recommendation)
            .options(
                selectinload(Recommendation.feedback),
                selectinload(Recommendation.outcome_snapshots),
                selectinload(Recommendation.candidate_plans),
            )
            .where(Recommendation.status == "completed")
            .order_by(Recommendation.created_at)
        )
        recommendations = result.scalars().all()

    rows: list[DatasetRow] = []
    for rec in recommendations:
        fb = rec.feedback[0] if rec.feedback else None
        outcome = rec.outcome_snapshots[0] if rec.outcome_snapshots else None

        hp_delta = outcome.hp_delta if outcome else None
        label = derive_quality_label(
            rating=fb.rating if fb else None,
            label=fb.label if fb else None,
            hp_delta=hp_delta,
        )

        selected = next(
            (cp.planner_output for cp in rec.candidate_plans if cp.is_selected), None
        )

        score_breakdowns = [
            cp.plan_score_json for cp in rec.candidate_plans if cp.plan_score_json
        ]
        influence_deltas = [
            {"plan_id": cp.plan_key, **cp.influence_delta_json}
            for cp in rec.candidate_plans
            if cp.influence_delta_json
        ]

        row = DatasetRow(
            recommendation_id=rec.id,
            state_view=rec.final_recommendation or {},
            features={},
            tactical_bundles=[],
            candidate_plans=[cp.planner_output or {} for cp in rec.candidate_plans],
            selected_plan=selected,
            score_breakdowns=score_breakdowns,
            influence_summary=rec.influence_summary_json,
            influence_findings=rec.influence_findings_json,
            plan_influence_deltas=influence_deltas or None,
            user_feedback={
                "rating": fb.rating,
                "label": fb.label,
                "comment": fb.comment,
                "followed_plan": fb.followed_plan,
            }
            if fb
            else None,
            outcome={
                "hp_delta": hp_delta,
                "fight_outcome_next_round": outcome.fight_outcome_next_round
                if outcome
                else None,
                "tower_lost_next_round": outcome.tower_lost_next_round
                if outcome
                else None,
            }
            if outcome
            else None,
            derived_quality_label=label,
        )
        rows.append(row)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(row.model_dump_json() + "\n")

    return len(rows)
