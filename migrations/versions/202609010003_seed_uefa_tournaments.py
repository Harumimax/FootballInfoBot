"""Seed UEFA tournaments

Revision ID: 202609010003
Revises: 202609010002
Create Date: 2026-09-01
"""

from __future__ import annotations

from alembic import op


revision = "202609010003"
down_revision = "202609010002"
branch_labels = None
depends_on = None


TOURNAMENTS = (
    ("league", "Лига чемпионов", "https://football.kulichki.net/league/"),
    ("uefa_cup", "Лига Европы", "https://football.kulichki.net/uefa_cup/"),
    ("lc", "Лига конференций", "https://football.kulichki.net/lc/"),
)


def upgrade() -> None:
    for code, name, source_url in TOURNAMENTS:
        op.execute(
            "INSERT INTO leagues (source, code, name, source_url, is_active) "
            f"VALUES ('kulichki', '{code}', '{name}', '{source_url}', true) "
            "ON CONFLICT (source, code) DO UPDATE SET "
            "name = EXCLUDED.name, source_url = EXCLUDED.source_url, is_active = true"
        )


def downgrade() -> None:
    op.execute("DELETE FROM leagues WHERE source = 'kulichki' AND code IN ('league', 'uefa_cup', 'lc')")
