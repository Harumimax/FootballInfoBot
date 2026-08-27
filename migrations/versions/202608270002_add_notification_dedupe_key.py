"""Add notification dedupe key

Revision ID: 202608270002
Revises: 202608270001
Create Date: 2026-08-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202608270002"
down_revision = "202608270001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notification_log", sa.Column("dedupe_key", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_notification_log_dedupe_key", "notification_log", ["dedupe_key"])


def downgrade() -> None:
    op.drop_constraint("uq_notification_log_dedupe_key", "notification_log", type_="unique")
    op.drop_column("notification_log", "dedupe_key")
