from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    teams: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    rounds: Mapped[list[Round]] = relationship(back_populates="match", cascade="all, delete-orphan")
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    match_id: Mapped[str] = mapped_column(String(36), ForeignKey("matches.id"))
    round_number: Mapped[int] = mapped_column(Integer)
    raw_round: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    state_view: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    match: Mapped[Match] = relationship(back_populates="rounds")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    match_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("matches.id"), nullable=True)
    round_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("rounds.id"), nullable=True)
    round_number: Mapped[int] = mapped_column(Integer)
    player_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    supply: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="created")
    final_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_recommendation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    placement: Mapped[list | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    match: Mapped[Match | None] = relationship(back_populates="recommendations")
    candidate_plans: Mapped[list[CandidatePlanRow]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )
    llm_calls: Mapped[list[LLMCall]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )
    feedback: Mapped[list[Feedback]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )
    outcome_snapshots: Mapped[list[OutcomeSnapshot]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan"
    )


class CandidatePlanRow(Base):
    __tablename__ = "candidate_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("recommendations.id"))
    plan_key: Mapped[str] = mapped_column(Text)
    planner_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    judge_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    recommendation: Mapped[Recommendation] = relationship(back_populates="candidate_plans")


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    recommendation_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("recommendations.id"), nullable=True
    )
    stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    recommendation: Mapped[Recommendation | None] = relationship(back_populates="llm_calls")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("recommendations.id"))
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    label: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    followed_plan: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    recommendation: Mapped[Recommendation] = relationship(back_populates="feedback")


class OutcomeSnapshot(Base):
    __tablename__ = "outcome_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    recommendation_id: Mapped[str] = mapped_column(String(36), ForeignKey("recommendations.id"))
    next_round_number: Mapped[int] = mapped_column(Integer)
    next_round_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)

    recommendation: Mapped[Recommendation] = relationship(back_populates="outcome_snapshots")
