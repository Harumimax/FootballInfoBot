from __future__ import annotations

from dataclasses import dataclass

from app.parser.dto import ParsedRound, ParsedStandingRow


@dataclass(frozen=True)
class TelegramUserProfile:
    telegram_user_id: int
    username: str | None
    display_name: str
    language_code: str | None


@dataclass(frozen=True)
class LeagueView:
    code: str
    name: str


@dataclass(frozen=True)
class SubscriptionToggleResult:
    league: LeagueView
    is_active: bool
    current_round: ParsedRound | None
    current_rounds: tuple[ParsedRound, ...] = ()


@dataclass(frozen=True)
class StandingTableView:
    league: LeagueView
    rows: tuple[ParsedStandingRow, ...]


@dataclass(frozen=True)
class CurrentRoundView:
    league: LeagueView
    round: ParsedRound | None
    rounds: tuple[ParsedRound, ...] = ()
