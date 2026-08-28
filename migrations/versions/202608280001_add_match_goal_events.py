"""Add match goal events

Revision ID: 202608280001
Revises: 202608270002
Create Date: 2026-08-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202608280001"
down_revision = "202608270002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "match_goal_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("minute", sa.String(length=16), nullable=False),
        sa.Column("scorer_name", sa.String(length=255), nullable=False),
        sa.Column("score_after", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", "position", name="uq_match_goal_events_match_position"),
    )
    op.create_index(op.f("ix_match_goal_events_match_id"), "match_goal_events", ["match_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_match_goal_events_match_id"), table_name="match_goal_events")
    op.drop_table("match_goal_events")
