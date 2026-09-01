"""Initial PostgreSQL schema

Revision ID: 202608270001
Revises: None
Create Date: 2026-08-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "202608270001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leagues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "code", name="uq_leagues_source_code"),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "normalized_name", name="uq_teams_source_normalized_name"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
    )
    op.create_table(
        "parser_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint("target_type in ('league_page', 'round_page', 'other')", name="ck_parser_runs_target_type"),
        sa.CheckConstraint("status in ('success', 'failed', 'skipped')", name="ck_parser_runs_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("source_season_key", sa.String(length=32), nullable=False),
        sa.Column("is_current", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("league_id", "source_season_key", name="uq_seasons_league_source_key"),
    )
    op.create_index(op.f("ix_seasons_league_id"), "seasons", ["league_id"], unique=False)
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_results", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_upcoming", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notify_digest", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "league_id", name="uq_subscriptions_user_league"),
    )
    op.create_index(op.f("ix_subscriptions_league_id"), "subscriptions", ["league_id"], unique=False)
    op.create_index(op.f("ix_subscriptions_user_id"), "subscriptions", ["user_id"], unique=False)
    op.create_table(
        "rounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status in ('planned', 'active', 'completed', 'unknown')", name="ck_rounds_status"),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_id", "round_number", name="uq_rounds_season_round_number"),
    )
    op.create_index(op.f("ix_rounds_league_id"), "rounds", ["league_id"], unique=False)
    op.create_index(op.f("ix_rounds_season_id"), "rounds", ["season_id"], unique=False)
    op.create_table(
        "standings_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_standings_snapshots_league_id"), "standings_snapshots", ["league_id"], unique=False)
    op.create_index(op.f("ix_standings_snapshots_season_id"), "standings_snapshots", ["season_id"], unique=False)
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("league_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.Integer(), nullable=True),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("raw_status", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status in ('scheduled', 'live', 'finished', 'postponed', 'cancelled', 'unknown')",
            name="ck_matches_status",
        ),
        sa.ForeignKeyConstraint(["away_team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["home_team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["season_id"], ["seasons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source",
            "league_id",
            "season_id",
            "round_id",
            "home_team_id",
            "away_team_id",
            name="uq_matches_source_round_team_pair",
        ),
    )
    op.create_index(op.f("ix_matches_away_team_id"), "matches", ["away_team_id"], unique=False)
    op.create_index(op.f("ix_matches_home_team_id"), "matches", ["home_team_id"], unique=False)
    op.create_index(op.f("ix_matches_league_id"), "matches", ["league_id"], unique=False)
    op.create_index(op.f("ix_matches_round_id"), "matches", ["round_id"], unique=False)
    op.create_index(op.f("ix_matches_scheduled_at"), "matches", ["scheduled_at"], unique=False)
    op.create_index(op.f("ix_matches_season_id"), "matches", ["season_id"], unique=False)
    op.create_table(
        "standings_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("played", sa.Integer(), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=True),
        sa.Column("draws", sa.Integer(), nullable=True),
        sa.Column("losses", sa.Integer(), nullable=True),
        sa.Column("goals_for", sa.Integer(), nullable=True),
        sa.Column("goals_against", sa.Integer(), nullable=True),
        sa.Column("goal_difference", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("raw_values", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["snapshot_id"], ["standings_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "team_id", name="uq_standings_rows_snapshot_team"),
    )
    op.create_index(op.f("ix_standings_rows_snapshot_id"), "standings_rows", ["snapshot_id"], unique=False)
    op.create_index(op.f("ix_standings_rows_team_id"), "standings_rows", ["team_id"], unique=False)
    op.create_table(
        "data_change_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("league_id", sa.Integer(), nullable=True),
        sa.Column("match_id", sa.Integer(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "event_type in ('match_created', 'match_updated', 'match_finished', 'standings_updated')",
            name="ck_data_change_events_event_type",
        ),
        sa.ForeignKeyConstraint(["league_id"], ["leagues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_change_events_league_id"), "data_change_events", ["league_id"], unique=False)
    op.create_index(op.f("ix_data_change_events_match_id"), "data_change_events", ["match_id"], unique=False)
    op.create_index(op.f("ix_data_change_events_processed_at"), "data_change_events", ["processed_at"], unique=False)
    op.create_table(
        "notification_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("change_event_id", sa.Integer(), nullable=True),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("message_type in ('result', 'reminder', 'digest', 'system')", name="ck_notification_log_message_type"),
        sa.CheckConstraint("status in ('sent', 'failed', 'skipped')", name="ck_notification_log_status"),
        sa.ForeignKeyConstraint(["change_event_id"], ["data_change_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "change_event_id", "message_type", name="uq_notification_log_user_event_type"),
    )
    op.create_index(op.f("ix_notification_log_change_event_id"), "notification_log", ["change_event_id"], unique=False)
    op.create_index(op.f("ix_notification_log_subscription_id"), "notification_log", ["subscription_id"], unique=False)
    op.create_index(op.f("ix_notification_log_user_id"), "notification_log", ["user_id"], unique=False)

    op.bulk_insert(
        sa.table(
            "leagues",
            sa.column("source", sa.String()),
            sa.column("code", sa.String()),
            sa.column("name", sa.String()),
            sa.column("source_url", sa.Text()),
            sa.column("is_active", sa.Boolean()),
        ),
        [
            {
                "source": "kulichki",
                "code": "england",
                "name": "Англия",
                "source_url": "https://football.kulichki.net/england/",
                "is_active": True,
            },
            {
                "source": "kulichki",
                "code": "spain",
                "name": "Испания",
                "source_url": "https://football.kulichki.net/spain/",
                "is_active": True,
            },
            {
                "source": "kulichki",
                "code": "germany",
                "name": "Германия",
                "source_url": "https://football.kulichki.net/germany/",
                "is_active": True,
            },
            {
                "source": "kulichki",
                "code": "italy",
                "name": "Италия",
                "source_url": "https://football.kulichki.net/italy/",
                "is_active": True,
            },
            {
                "source": "kulichki",
                "code": "france",
                "name": "Франция",
                "source_url": "https://football.kulichki.net/france/",
                "is_active": True,
            },
            {
                "source": "kulichki",
                "code": "ruschamp",
                "name": "Россия",
                "source_url": "https://football.kulichki.net/ruschamp/",
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_log_user_id"), table_name="notification_log")
    op.drop_index(op.f("ix_notification_log_subscription_id"), table_name="notification_log")
    op.drop_index(op.f("ix_notification_log_change_event_id"), table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_index(op.f("ix_data_change_events_processed_at"), table_name="data_change_events")
    op.drop_index(op.f("ix_data_change_events_match_id"), table_name="data_change_events")
    op.drop_index(op.f("ix_data_change_events_league_id"), table_name="data_change_events")
    op.drop_table("data_change_events")
    op.drop_index(op.f("ix_standings_rows_team_id"), table_name="standings_rows")
    op.drop_index(op.f("ix_standings_rows_snapshot_id"), table_name="standings_rows")
    op.drop_table("standings_rows")
    op.drop_index(op.f("ix_matches_season_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_scheduled_at"), table_name="matches")
    op.drop_index(op.f("ix_matches_round_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_league_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_home_team_id"), table_name="matches")
    op.drop_index(op.f("ix_matches_away_team_id"), table_name="matches")
    op.drop_table("matches")
    op.drop_index(op.f("ix_standings_snapshots_season_id"), table_name="standings_snapshots")
    op.drop_index(op.f("ix_standings_snapshots_league_id"), table_name="standings_snapshots")
    op.drop_table("standings_snapshots")
    op.drop_index(op.f("ix_rounds_season_id"), table_name="rounds")
    op.drop_index(op.f("ix_rounds_league_id"), table_name="rounds")
    op.drop_table("rounds")
    op.drop_index(op.f("ix_subscriptions_user_id"), table_name="subscriptions")
    op.drop_index(op.f("ix_subscriptions_league_id"), table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index(op.f("ix_seasons_league_id"), table_name="seasons")
    op.drop_table("seasons")
    op.drop_table("parser_runs")
    op.drop_table("users")
    op.drop_table("teams")
    op.drop_table("leagues")
