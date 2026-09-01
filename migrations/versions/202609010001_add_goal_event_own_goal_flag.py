"""Add goal event own goal flag

Revision ID: 202609010001
Revises: 202608280003
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202609010001"
down_revision = "202608280003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "match_goal_events",
        sa.Column("is_own_goal", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("match_goal_events", "is_own_goal")
