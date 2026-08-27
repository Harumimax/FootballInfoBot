from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.parser.clients.http import FetchedPage
from app.parser.dto import LeaguePageData


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
            return LeagueSyncResult(
                league_code=league.code,
                status="success",
                fetched_url=page.url,
                http_status=page.status_code,
                current_round_number=current_round.number if current_round is not None else None,
                parsed_matches=len(current_round.matches) if current_round is not None else 0,
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
