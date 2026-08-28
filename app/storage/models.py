from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class League(TimestampMixin, Base):
    __tablename__ = "leagues"
    __table_args__ = (UniqueConstraint("source", "code", name="uq_leagues_source_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    seasons: Mapped[list[Season]] = relationship(back_populates="league")
    rounds: Mapped[list[Round]] = relationship(back_populates="league")
    matches: Mapped[list[Match]] = relationship(back_populates="league")
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="league")
    team_subscriptions: Mapped[list[TeamSubscription]] = relationship(back_populates="league")


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("league_id", "source_season_key", name="uq_seasons_league_source_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    source_season_key: Mapped[str] = mapped_column(String(32), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    league: Mapped[League] = relationship(back_populates="seasons")
    rounds: Mapped[list[Round]] = relationship(back_populates="season")
    matches: Mapped[list[Match]] = relationship(back_populates="season")
    standings_snapshots: Mapped[list[StandingSnapshot]] = relationship(back_populates="season")


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("source", "normalized_name", name="uq_teams_source_normalized_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    team_subscriptions: Mapped[list[TeamSubscription]] = relationship(back_populates="team")


class Round(TimestampMixin, Base):
    __tablename__ = "rounds"
    __table_args__ = (
        UniqueConstraint("season_id", "round_number", name="uq_rounds_season_round_number"),
        CheckConstraint("status in ('planned', 'active', 'completed', 'unknown')", name="ck_rounds_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="unknown")

    league: Mapped[League] = relationship(back_populates="rounds")
    season: Mapped[Season] = relationship(back_populates="rounds")
    matches: Mapped[list[Match]] = relationship(back_populates="round")


class Match(TimestampMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "league_id",
            "season_id",
            "round_id",
            "home_team_id",
            "away_team_id",
            name="uq_matches_source_round_team_pair",
        ),
        CheckConstraint(
            "status in ('scheduled', 'live', 'finished', 'postponed', 'cancelled', 'unknown')",
            name="ck_matches_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False, index=True)
    round_id: Mapped[int | None] = mapped_column(ForeignKey("rounds.id", ondelete="SET NULL"), index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="unknown")
    raw_status: Mapped[str | None] = mapped_column(String(255))

    league: Mapped[League] = relationship(back_populates="matches")
    season: Mapped[Season] = relationship(back_populates="matches")
    round: Mapped[Round | None] = relationship(back_populates="matches")
    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    change_events: Mapped[list[DataChangeEvent]] = relationship(back_populates="match")
    goal_events: Mapped[list[MatchGoalEvent]] = relationship(back_populates="match", cascade="all, delete-orphan")


class MatchGoalEvent(TimestampMixin, Base):
    __tablename__ = "match_goal_events"
    __table_args__ = (UniqueConstraint("match_id", "position", name="uq_match_goal_events_match_position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    minute: Mapped[str] = mapped_column(String(16), nullable=False)
    scorer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    score_after: Mapped[str | None] = mapped_column(String(16))

    match: Mapped[Match] = relationship(back_populates="goal_events")


class StandingSnapshot(Base):
    __tablename__ = "standings_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    league: Mapped[League] = relationship()
    season: Mapped[Season] = relationship(back_populates="standings_snapshots")
    rows: Mapped[list[StandingRow]] = relationship(back_populates="snapshot", cascade="all, delete-orphan")


class StandingRow(Base):
    __tablename__ = "standings_rows"
    __table_args__ = (UniqueConstraint("snapshot_id", "team_id", name="uq_standings_rows_snapshot_team"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("standings_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    played: Mapped[int | None] = mapped_column(Integer)
    wins: Mapped[int | None] = mapped_column(Integer)
    draws: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    goals_for: Mapped[int | None] = mapped_column(Integer)
    goals_against: Mapped[int | None] = mapped_column(Integer)
    goal_difference: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[int | None] = mapped_column(Integer)
    raw_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    snapshot: Mapped[StandingSnapshot] = relationship(back_populates="rows")
    team: Mapped[Team] = relationship()


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(16))

    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="user")
    team_subscriptions: Mapped[list[TeamSubscription]] = relationship(back_populates="user")
    notification_logs: Mapped[list[NotificationLog]] = relationship(back_populates="user")


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "league_id", name="uq_subscriptions_user_league"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notify_results: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notify_upcoming: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notify_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    user: Mapped[User] = relationship(back_populates="subscriptions")
    league: Mapped[League] = relationship(back_populates="subscriptions")


class TeamSubscription(TimestampMixin, Base):
    __tablename__ = "team_subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "league_id", "team_id", name="uq_team_subscriptions_user_league_team"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notify_results: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notify_upcoming: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    notify_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    user: Mapped[User] = relationship(back_populates="team_subscriptions")
    league: Mapped[League] = relationship(back_populates="team_subscriptions")
    team: Mapped[Team] = relationship(back_populates="team_subscriptions")


class ParserRun(Base):
    __tablename__ = "parser_runs"
    __table_args__ = (
        CheckConstraint("target_type in ('league_page', 'round_page', 'other')", name="ck_parser_runs_target_type"),
        CheckConstraint("status in ('success', 'failed', 'skipped')", name="ck_parser_runs_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    http_status: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)


class DataChangeEvent(Base):
    __tablename__ = "data_change_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('match_created', 'match_updated', 'match_finished', 'standings_updated')",
            name="ck_data_change_events_event_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("leagues.id", ondelete="CASCADE"), index=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    league: Mapped[League | None] = relationship()
    match: Mapped[Match | None] = relationship(back_populates="change_events")
    notification_logs: Mapped[list[NotificationLog]] = relationship(back_populates="change_event")


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint("user_id", "change_event_id", "message_type", name="uq_notification_log_user_event_type"),
        UniqueConstraint("dedupe_key", name="uq_notification_log_dedupe_key"),
        CheckConstraint("message_type in ('result', 'reminder', 'digest', 'system')", name="ck_notification_log_message_type"),
        CheckConstraint("status in ('sent', 'failed', 'skipped')", name="ck_notification_log_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id", ondelete="SET NULL"), index=True)
    change_event_id: Mapped[int | None] = mapped_column(ForeignKey("data_change_events.id", ondelete="SET NULL"), index=True)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(255))
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="notification_logs")
    subscription: Mapped[Subscription | None] = relationship()
    change_event: Mapped[DataChangeEvent | None] = relationship(back_populates="notification_logs")
