from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ParsedLeague:
    code: str
    name: str
    source_url: str


@dataclass(frozen=True)
class ParsedMatch:
    home_team: str
    away_team: str
    scheduled_at: datetime | None
    home_score: int | None
    away_score: int | None
    status: str
    source_url: str | None = None


@dataclass(frozen=True)
class ParsedRound:
    number: int
    source_url: str | None
    matches: tuple[ParsedMatch, ...]


@dataclass(frozen=True)
class ParsedStandingRow:
    position: int
    team_name: str
    played: int | None
    points: int | None
    wins: int | None = None
    draws: int | None = None
    losses: int | None = None
    goals_for: int | None = None
    goals_against: int | None = None
    goal_difference: int | None = None


@dataclass(frozen=True)
class LeaguePageData:
    league: ParsedLeague
    season_label: str | None
    source_season_key: str | None
    current_round: ParsedRound | None
    standings: tuple[ParsedStandingRow, ...]
    rounds: tuple[ParsedRound, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RoundPageData:
    league: ParsedLeague
    season_label: str | None
    source_season_key: str | None
    round: ParsedRound
