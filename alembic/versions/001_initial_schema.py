"""Initial schema — all v1 tables.

Revision ID: 001
Revises:
Create Date: 2026-06-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_file", sa.Text, nullable=True),
        sa.Column("match_mode", sa.Text, nullable=True),
        sa.Column("player_name", sa.Text, nullable=True),
        sa.Column("teams", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "rounds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("raw_round", postgresql.JSONB, nullable=True),
        sa.Column("state_view", postgresql.JSONB, nullable=True),
        sa.Column("features", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("match_id", sa.String(36), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column("round_id", sa.String(36), sa.ForeignKey("rounds.id"), nullable=True),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("player_name", sa.Text, nullable=True),
        sa.Column("supply", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="created"),
        sa.Column("final_summary", sa.Text, nullable=True),
        sa.Column("final_recommendation", postgresql.JSONB, nullable=True),
        sa.Column("placement", postgresql.JSONB, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("prompt_version", sa.Text, nullable=True),
        sa.Column("model_name", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "candidate_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.String(36),
            sa.ForeignKey("recommendations.id"),
            nullable=False,
        ),
        sa.Column("plan_key", sa.Text, nullable=False),
        sa.Column("planner_output", postgresql.JSONB, nullable=True),
        sa.Column("validation_result", postgresql.JSONB, nullable=True),
        sa.Column("judge_score", sa.Float, nullable=True),
        sa.Column("is_selected", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.String(36),
            sa.ForeignKey("recommendations.id"),
            nullable=True,
        ),
        sa.Column("stage", sa.Text, nullable=True),
        sa.Column("provider", sa.Text, nullable=True),
        sa.Column("model", sa.Text, nullable=True),
        sa.Column("prompt_version", sa.Text, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("request_json", postgresql.JSONB, nullable=True),
        sa.Column("response_json", postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.String(36),
            sa.ForeignKey("recommendations.id"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("label", sa.Text, nullable=True),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("followed_plan", sa.Boolean, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "outcome_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "recommendation_id",
            sa.String(36),
            sa.ForeignKey("recommendations.id"),
            nullable=False,
        ),
        sa.Column("next_round_number", sa.Integer, nullable=False),
        sa.Column("next_round_state", postgresql.JSONB, nullable=True),
        sa.Column("result_summary", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("outcome_snapshots")
    op.drop_table("feedback")
    op.drop_table("llm_calls")
    op.drop_table("candidate_plans")
    op.drop_table("recommendations")
    op.drop_table("rounds")
    op.drop_table("matches")
