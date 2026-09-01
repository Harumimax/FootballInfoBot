"""Seed Russia league

Revision ID: 202609010002
Revises: 202609010001
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op


revision = "202609010002"
down_revision = "202609010001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO leagues (source, code, name, source_url, is_active) "
        "VALUES ('kulichki', 'ruschamp', 'Россия', 'https://football.kulichki.net/ruschamp/', true) "
        "ON CONFLICT (source, code) DO UPDATE SET "
        "name = EXCLUDED.name, source_url = EXCLUDED.source_url, is_active = true"
    )


def downgrade() -> None:
    op.execute("DELETE FROM leagues WHERE source = 'kulichki' AND code = 'ruschamp'")
