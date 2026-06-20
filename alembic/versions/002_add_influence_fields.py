"""Add influence JSON fields to recommendations and candidate_plans.

Revision ID: 002
Revises: 001
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "recommendations",
        sa.Column("influence_summary_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "recommendations",
        sa.Column("influence_findings_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "candidate_plans",
        sa.Column("plan_score_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "candidate_plans",
        sa.Column("influence_delta_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("candidate_plans", "influence_delta_json")
    op.drop_column("candidate_plans", "plan_score_json")
    op.drop_column("recommendations", "influence_findings_json")
    op.drop_column("recommendations", "influence_summary_json")
