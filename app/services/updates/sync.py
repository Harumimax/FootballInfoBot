from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Protocol

from app.parser.clients.http import FetchedPage
from app.parser.dto import LeaguePageData, ParsedGoalEvent, ParsedMatch, ParsedRound


@dataclass(frozen=True)
class LeagueSource:
    code: str
    name: str
    url: str
    source: str = "kulichki"
    is_active: bool = True


@dataclass(frozen=True)
class SaveLeaguePageResult:
    created_matches: int = 0
    updated_matches: int = 0
    created_change_events: int = 0


@dataclass(frozen=True)
class ParserRunDraft:
    source: str
    target_type: str
    target_url: str
    status: str
    started_at: datetime
    finished_at: datetime
    http_status: int | None = None
    error_message: str | None = None


@dataclass(frozen=True)
class LeagueSyncResult:
    league_code: str
    status: str
    fetched_url: str | None = None
    http_status: int | None = None
    current_round_number: int | None = None
    parsed_matches: int = 0
    parsed_standings_rows: int = 0
    created_matches: int = 0
    updated_matches: int = 0
    created_change_events: int = 0
    error_message: str | None = None


class PageClient(Protocol):
    async def fetch(self, url: str) -> FetchedPage:
        pass


class LeaguePageParser(Protocol):
    def parse_league_page(self, html: str, *, url: str, league_code: str, league_name: str) -> LeaguePageData:
        pass

    def parse_match_page(self, html: str, *, url: str) -> tuple[ParsedGoalEvent, ...]:
        pass


class FootballDataRepository(Protocol):
    async def save_league_page_data(self, data: LeaguePageData) -> SaveLeaguePageResult:
        pass

    async def record_parser_run(self, run: ParserRunDraft) -> None:
        pass


class LeagueSyncService:
    def __init__(
        self,
        *,
        page_client: PageClient,
        parser: LeaguePageParser,
        repository: FootballDataRepository,
        league_sources: tuple[LeagueSource, ...],
    ) -> None:
        self._page_client = page_client
        self._parser = parser
        self._repository = repository
        self._league_sources = {league.code: league for league in league_sources}

    async def sync_league(self, league_code: str) -> LeagueSyncResult:
        league = self._league_sources.get(league_code)
        if league is None:
            raise ValueError(f"Unknown league code: {league_code}")

        started_at = datetime.now(tz=None).astimezone()

        if not league.is_active:
            finished_at = datetime.now(tz=None).astimezone()
            await self._repository.record_parser_run(
                ParserRunDraft(
                    source=league.source,
                    target_type="league_page",
                    target_url=league.url,
                    status="skipped",
                    started_at=started_at,
                    finished_at=finished_at,
                    error_message="League source is disabled",
                )
            )
            return LeagueSyncResult(league_code=league.code, status="skipped", fetched_url=league.url)

        try:
            page = await self._page_client.fetch(league.url)
            parsed_data = self._parser.parse_league_page(
                page.html,
                url=page.url,
                league_code=league.code,
                league_name=league.name,
            )
            parsed_data = await self._include_next_round_if_current_finished(parsed_data)
            parsed_data = await self._enrich_match_goal_events(parsed_data)
            save_result = await self._repository.save_league_page_data(parsed_data)
            finished_at = datetime.now(tz=None).astimezone()
            await self._repository.record_parser_run(
                ParserRunDraft(
                    source=league.source,
                    target_type="league_page",
                    target_url=page.url,
                    status="success",
                    started_at=started_at,
                    finished_at=finished_at,
                    http_status=page.status_code,
                )
            )

            current_round = parsed_data.current_round
            parsed_matches = sum(len(round_.matches) for round_ in parsed_data.rounds)
            if parsed_matches == 0 and current_round is not None:
                parsed_matches = len(current_round.matches)
            return LeagueSyncResult(
                league_code=league.code,
                status="success",
                fetched_url=page.url,
                http_status=page.status_code,
                current_round_number=current_round.number if current_round is not None else None,
                parsed_matches=parsed_matches,
                parsed_standings_rows=len(parsed_data.standings),
                created_matches=save_result.created_matches,
                updated_matches=save_result.updated_matches,
                created_change_events=save_result.created_change_events,
            )
        except Exception as error:
            finished_at = datetime.now(tz=None).astimezone()
            await self._repository.record_parser_run(
                ParserRunDraft(
                    source=league.source,
                    target_type="league_page",
                    target_url=league.url,
                    status="failed",
                    started_at=started_at,
                    finished_at=finished_at,
                    error_message=str(error),
                )
            )
            return LeagueSyncResult(
                league_code=league.code,
                status="failed",
                fetched_url=league.url,
                error_message=str(error),
            )

    async def _include_next_round_if_current_finished(self, data: LeaguePageData) -> LeaguePageData:
        current_round = data.current_round
        if current_round is None or not _is_round_finished(current_round):
            return data

        next_round_number = current_round.number + 1
        next_round_url = _next_round_url(current_round.source_url, current_round.number)
        if next_round_url is None:
            return data

        try:
            page = await self._page_client.fetch(next_round_url)
            next_page_data = self._parser.parse_league_page(
                page.html,
                url=page.url,
                league_code=data.league.code,
                league_name=data.league.name,
            )
        except Exception:
            return data

        source_rounds = _iter_source_rounds(data)
        existing_numbers = {round_.number for round_ in source_rounds}
        new_rounds = tuple(
            round_
            for round_ in _iter_source_rounds(next_page_data)
            if round_.matches and round_.number not in existing_numbers
        )
        has_next_round = next_round_number in existing_numbers or any(
            round_.number == next_round_number for round_ in new_rounds
        )
        if not has_next_round:
            return data

        return replace(data, rounds=(*source_rounds, *new_rounds))

    async def _enrich_match_goal_events(self, data: LeaguePageData) -> LeaguePageData:
        fetched_goal_events: dict[str, tuple[ParsedGoalEvent, ...]] = {}

        async def enrich_match(match: ParsedMatch) -> ParsedMatch:
            if not _should_fetch_goal_events(match):
                return match
            assert match.source_url is not None
            if match.source_url not in fetched_goal_events:
                try:
                    page = await self._page_client.fetch(match.source_url)
                    fetched_goal_events[match.source_url] = self._parser.parse_match_page(page.html, url=page.url)
                except Exception:
                    return match
            return replace(match, goal_events=fetched_goal_events[match.source_url], goal_events_loaded=True)

        async def enrich_round(round_: ParsedRound) -> ParsedRound:
            return replace(round_, matches=tuple([await enrich_match(match) for match in round_.matches]))

        source_rounds = data.rounds or ((data.current_round,) if data.current_round is not None else ())
        rounds = tuple([await enrich_round(round_) for round_ in source_rounds])
        current_round = data.current_round
        if current_round is not None:
            current_round = next((round_ for round_ in rounds if round_.number == current_round.number), current_round)

        return replace(data, current_round=current_round, rounds=rounds)


def _is_round_finished(round_: ParsedRound) -> bool:
    if not round_.matches:
        return False
    return all(match.status in {"finished", "postponed", "cancelled"} for match in round_.matches)


def _next_round_url(source_url: str | None, current_round_number: int) -> str | None:
    if source_url is None:
        return None
    current_part = f"/{current_round_number}/"
    if current_part not in source_url:
        return None
    return source_url.replace(current_part, f"/{current_round_number + 1}/", 1)


def _iter_source_rounds(data: LeaguePageData) -> tuple[ParsedRound, ...]:
    if data.rounds:
        return data.rounds
    if data.current_round is not None:
        return (data.current_round,)
    return ()


def _should_fetch_goal_events(match: ParsedMatch) -> bool:
    if match.source_url is None:
        return False
    if match.status not in {"finished", "live"}:
        return False
    return match.home_score is not None and match.away_score is not None
