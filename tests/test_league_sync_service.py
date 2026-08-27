from __future__ import annotations

import unittest
from pathlib import Path

from app.parser.clients.http import FetchedPage
from app.parser.dto import LeaguePageData
from app.parser.kulichki import KulichkiParser
from app.services.updates import LeagueSource, LeagueSyncService, ParserRunDraft, SaveLeaguePageResult
from app.storage.repositories import normalize_team_name


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "kulichki"


class FakePageClient:
    def __init__(self, page: FetchedPage | None = None, error: Exception | None = None) -> None:
        self.page = page
        self.error = error
        self.fetched_urls: list[str] = []

    async def fetch(self, url: str) -> FetchedPage:
        self.fetched_urls.append(url)
        if self.error is not None:
            raise self.error
        assert self.page is not None
        return self.page


class FakeFootballDataRepository:
    def __init__(self, save_result: SaveLeaguePageResult | None = None) -> None:
        self.save_result = save_result or SaveLeaguePageResult()
        self.saved_pages: list[LeaguePageData] = []
        self.parser_runs: list[ParserRunDraft] = []

    async def save_league_page_data(self, data: LeaguePageData) -> SaveLeaguePageResult:
        self.saved_pages.append(data)
        return self.save_result

    async def record_parser_run(self, run: ParserRunDraft) -> None:
        self.parser_runs.append(run)


class LeagueSyncServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_sync_league_fetches_parses_saves_and_records_success(self) -> None:
        html = _read_fixture("england_league.html")
        client = FakePageClient(
            FetchedPage(
                url="https://football.kulichki.net/england/",
                html=html,
                status_code=200,
            )
        )
        repository = FakeFootballDataRepository(
            SaveLeaguePageResult(created_matches=2, updated_matches=0, created_change_events=2)
        )
        service = LeagueSyncService(
            page_client=client,
            parser=KulichkiParser(base_url="https://football.kulichki.net"),
            repository=repository,
            league_sources=(
                LeagueSource(code="england", name="Англия", url="https://football.kulichki.net/england/"),
            ),
        )

        result = await service.sync_league("england")

        self.assertEqual(result.status, "success")
        self.assertEqual(result.league_code, "england")
        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.current_round_number, 1)
        self.assertEqual(result.parsed_matches, 2)
        self.assertEqual(result.parsed_standings_rows, 2)
        self.assertEqual(result.created_matches, 2)
        self.assertEqual(result.created_change_events, 2)
        self.assertEqual(client.fetched_urls, ["https://football.kulichki.net/england/"])
        self.assertEqual(len(repository.saved_pages), 1)
        self.assertEqual(repository.parser_runs[-1].status, "success")

    async def test_sync_league_counts_all_visible_round_matches(self) -> None:
        html = _read_fixture("spain_league_live.html")
        client = FakePageClient(
            FetchedPage(
                url="https://football.kulichki.net/spain/",
                html=html,
                status_code=200,
            )
        )
        service = LeagueSyncService(
            page_client=client,
            parser=KulichkiParser(base_url="https://football.kulichki.net"),
            repository=FakeFootballDataRepository(),
            league_sources=(
                LeagueSource(code="spain", name="Испания", url="https://football.kulichki.net/spain/"),
            ),
        )

        result = await service.sync_league("spain")

        self.assertEqual(result.status, "success")
        self.assertEqual(result.current_round_number, 3)
        self.assertEqual(result.parsed_matches, 14)

    async def test_sync_league_records_failed_parser_run_when_fetch_fails(self) -> None:
        client = FakePageClient(error=RuntimeError("source unavailable"))
        repository = FakeFootballDataRepository()
        service = LeagueSyncService(
            page_client=client,
            parser=KulichkiParser(base_url="https://football.kulichki.net"),
            repository=repository,
            league_sources=(
                LeagueSource(code="spain", name="Испания", url="https://football.kulichki.net/spain/"),
            ),
        )

        result = await service.sync_league("spain")

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_message, "source unavailable")
        self.assertEqual(repository.parser_runs[-1].status, "failed")
        self.assertEqual(repository.parser_runs[-1].error_message, "source unavailable")
        self.assertEqual(repository.saved_pages, [])

    async def test_sync_league_skips_disabled_source(self) -> None:
        client = FakePageClient()
        repository = FakeFootballDataRepository()
        service = LeagueSyncService(
            page_client=client,
            parser=KulichkiParser(base_url="https://football.kulichki.net"),
            repository=repository,
            league_sources=(
                LeagueSource(
                    code="spain",
                    name="Испания",
                    url="https://football.kulichki.net/spain/",
                    is_active=False,
                ),
            ),
        )

        result = await service.sync_league("spain")

        self.assertEqual(result.status, "skipped")
        self.assertEqual(client.fetched_urls, [])
        self.assertEqual(repository.parser_runs[-1].status, "skipped")

    async def test_sync_league_rejects_unknown_league_code(self) -> None:
        service = LeagueSyncService(
            page_client=FakePageClient(),
            parser=KulichkiParser(base_url="https://football.kulichki.net"),
            repository=FakeFootballDataRepository(),
            league_sources=(),
        )

        with self.assertRaises(ValueError):
            await service.sync_league("unknown")

    def test_normalize_team_name_collapses_spaces_and_casefolds(self) -> None:
        self.assertEqual(normalize_team_name("  Реал   Мадрид  "), "реал мадрид")


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
