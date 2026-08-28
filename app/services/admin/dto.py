from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.services.subscriptions.dto import LeagueView, TeamView


@dataclass(frozen=True)
class LeagueParserStatusView:
    league_name: str
    last_success_at: datetime | None
    is_active: bool


@dataclass(frozen=True)
class ParserStatusView:
    leagues: tuple[LeagueParserStatusView, ...]
    last_run_at: datetime | None = None
    last_run_status: str | None = None
    last_error: str | None = None


@dataclass(frozen=True)
class AdminSyncResult:
    league_name: str
    status: str
    parsed_matches: int
    parsed_standings_rows: int
    error_message: str | None = None


@dataclass(frozen=True)
class LeagueToggleResult:
    league_name: str
    is_active: bool


@dataclass(frozen=True)
class AdminSubscriptionStatsView:
    users_count: int
    active_league_subscriptions: int
    active_team_subscriptions: int


@dataclass(frozen=True)
class RecentNotificationView:
    created_at: datetime
    telegram_user_id: int
    message_type: str
    status: str
    dedupe_key: str | None
    error_message: str | None = None


@dataclass(frozen=True)
class AdminTeamListView:
    league: LeagueView
    teams: tuple[TeamView, ...]
