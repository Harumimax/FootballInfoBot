from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Callable, Protocol

from app.bot.messages import LeagueView, render_round_state, render_rounds_state
from app.parser.dto import ParsedRound


MORNING_PUSH_TIME = time(hour=9, minute=0)
AFTER_MATCHDAY_FIRST_CHECK_TIME = time(hour=23, minute=0)
AFTER_MATCHDAY_LAST_CHECK_TIME = time(hour=3, minute=0)


class PushKind(StrEnum):
    MORNING = "morning"
    AFTER_MATCHDAY = "after_matchday"


@dataclass(frozen=True)
class LeagueRoundState:
    league: LeagueView
    round: ParsedRound | None
    has_match_today: bool
    all_today_matches_finished: bool
    has_changes_today: bool
    rounds: tuple[ParsedRound, ...] = ()


@dataclass(frozen=True)
class SubscriberView:
    user_id: int
    telegram_user_id: int


@dataclass(frozen=True)
class PushNotification:
    telegram_user_id: int
    league_code: str
    kind: PushKind
    match_date: date
    text: str

    @property
    def dedupe_key(self) -> str:
        return f"{self.kind.value}:{self.match_date.isoformat()}:{self.league_code}:{self.telegram_user_id}"


@dataclass(frozen=True)
class PushRunResult:
    kind: PushKind
    checked_at: datetime
    sent_count: int
    skipped_leagues: tuple[str, ...]
    pending_leagues: tuple[str, ...] = ()


class PushDataRepository(Protocol):
    async def get_active_league_round_states(self, match_date: date) -> tuple[LeagueRoundState, ...]:
        pass

    async def get_active_subscribers_for_league(self, league_code: str) -> tuple[SubscriberView, ...]:
        pass

    async def was_notification_sent(self, dedupe_key: str) -> bool:
        pass

    async def record_notification_sent(self, notification: PushNotification) -> None:
        pass


class PushSender(Protocol):
    async def send(self, notification: PushNotification) -> None:
        pass


class PushNotificationService:
    def __init__(self, *, repository: PushDataRepository, sender: PushSender) -> None:
        self._repository = repository
        self._sender = sender

    async def send_morning_pushes(self, checked_at: datetime) -> PushRunResult:
        sent_count, skipped_leagues = await self._send_ready_league_states(
            kind=PushKind.MORNING,
            checked_at=checked_at,
            is_ready=lambda state: state.has_match_today,
        )

        return PushRunResult(
            kind=PushKind.MORNING,
            checked_at=checked_at,
            sent_count=sent_count,
            skipped_leagues=tuple(skipped_leagues),
        )

    async def check_after_matchday_pushes(self, checked_at: datetime) -> PushRunResult:
        pending_leagues: list[str] = []
        match_date = after_matchday_target_date(checked_at)

        def is_ready(state: LeagueRoundState) -> bool:
            if not state.has_match_today:
                return False
            if state.all_today_matches_finished:
                return True
            if _is_last_after_matchday_check(checked_at) and state.has_changes_today:
                return True
            pending_leagues.append(state.league.code)
            return False

        sent_count, skipped_leagues = await self._send_ready_league_states(
            kind=PushKind.AFTER_MATCHDAY,
            checked_at=checked_at,
            match_date=match_date,
            is_ready=is_ready,
        )

        return PushRunResult(
            kind=PushKind.AFTER_MATCHDAY,
            checked_at=checked_at,
            sent_count=sent_count,
            skipped_leagues=tuple(skipped_leagues),
            pending_leagues=tuple(pending_leagues),
        )

    async def _send_ready_league_states(
        self,
        *,
        kind: PushKind,
        checked_at: datetime,
        match_date: date | None = None,
        is_ready: Callable[[LeagueRoundState], bool],
    ) -> tuple[int, list[str]]:
        sent_count = 0
        skipped_leagues: list[str] = []
        match_date = match_date or checked_at.date()
        states = await self._repository.get_active_league_round_states(match_date)

        for state in states:
            if not is_ready(state):
                skipped_leagues.append(state.league.code)
                continue

            text = render_rounds_state(state.league.name, state.rounds) if state.rounds else render_round_state(state.league.name, state.round)
            subscribers = await self._repository.get_active_subscribers_for_league(state.league.code)

            for subscriber in subscribers:
                notification = PushNotification(
                    telegram_user_id=subscriber.telegram_user_id,
                    league_code=state.league.code,
                    kind=kind,
                    match_date=match_date,
                    text=text,
                )
                if await self._repository.was_notification_sent(notification.dedupe_key):
                    continue

                await self._sender.send(notification)
                await self._repository.record_notification_sent(notification)
                sent_count += 1

        return sent_count, skipped_leagues


def should_run_after_matchday_check(checked_at: datetime) -> bool:
    current_time = checked_at.time().replace(second=0, microsecond=0)
    return current_time >= AFTER_MATCHDAY_FIRST_CHECK_TIME or current_time <= AFTER_MATCHDAY_LAST_CHECK_TIME


def after_matchday_target_date(checked_at: datetime) -> date:
    current_time = checked_at.time().replace(second=0, microsecond=0)
    if current_time <= AFTER_MATCHDAY_LAST_CHECK_TIME:
        return checked_at.date() - timedelta(days=1)
    return checked_at.date()


def _is_last_after_matchday_check(checked_at: datetime) -> bool:
    current_time = checked_at.time().replace(second=0, microsecond=0)
    return current_time == AFTER_MATCHDAY_LAST_CHECK_TIME
