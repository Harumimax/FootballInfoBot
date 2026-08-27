from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
