"""Seed extra MVP leagues

Revision ID: 202608280003
Revises: 202608280002
Create Date: 2026-08-28
"""

from __future__ import annotations

from alembic import op


revision = "202608280003"
down_revision = "202608280002"
branch_labels = None
depends_on = None


EXTRA_LEAGUES = (
    ("germany", "Германия", "https://football.kulichki.net/germany/"),
    ("italy", "Италия", "https://football.kulichki.net/italy/"),
    ("france", "Франция", "https://football.kulichki.net/france/"),
)


def upgrade() -> None:
    for code, name, source_url in EXTRA_LEAGUES:
        op.execute(
            "INSERT INTO leagues (source, code, name, source_url, is_active) "
            f"VALUES ('kulichki', '{code}', '{name}', '{source_url}', true) "
            "ON CONFLICT (source, code) DO UPDATE SET "
            f"name = EXCLUDED.name, source_url = EXCLUDED.source_url, is_active = true"
        )


def downgrade() -> None:
    op.execute("DELETE FROM leagues WHERE source = 'kulichki' AND code IN ('germany', 'italy', 'france')")
