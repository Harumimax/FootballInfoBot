"""Add team subscriptions

Revision ID: 202608280002
Revises: 202608280001
Create Date: 2026-08-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202608280002"
down_revision = "202608280001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_results", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_upcoming", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_digest", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "league_id", "team_id", name="uq_team_subscriptions_user_league_team"),
    )
    op.create_index(op.f("ix_team_subscriptions_league_id"), "team_subscriptions", ["league_id"], unique=False)
    op.create_index(op.f("ix_team_subscriptions_team_id"), "team_subscriptions", ["team_id"], unique=False)
    op.create_index(op.f("ix_team_subscriptions_user_id"), "team_subscriptions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_team_subscriptions_user_id"), table_name="team_subscriptions")
    op.drop_index(op.f("ix_team_subscriptions_team_id"), table_name="team_subscriptions")
    op.drop_index(op.f("ix_team_subscriptions_league_id"), table_name="team_subscriptions")
    op.drop_table("team_subscriptions")
