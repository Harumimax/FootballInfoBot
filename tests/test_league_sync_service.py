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
    def __init__(
        self,
        page: FetchedPage | None = None,
        *,
        pages_by_url: dict[str, FetchedPage] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.page = page
        self.pages_by_url = pages_by_url or {}
        self.error = error
        self.fetched_urls: list[str] = []

    async def fetch(self, url: str) -> FetchedPage:
        self.fetched_urls.append(url)
        if self.error is not None:
            raise self.error
        if url in self.pages_by_url:
            return self.pages_by_url[url]
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

    async def test_sync_league_fetches_next_round_when_current_round_is_finished(self) -> None:
        league_url = "https://football.kulichki.net/fnl/"
        next_round_url = "https://football.kulichki.net/fnl/2027/10/"
        league_html = """
        <html>
            <body data-current-round="9">
                <h1>ФНЛ 2026/2027</h1>
                <section data-current-round="9">
                    <h2>9-й тур</h2>
                    <div data-match>
                        <span data-match-date>30.08.2026</span>
                        <span data-match-time>19:00</span>
                        <span data-home-team>Арсенал</span>
                        <span data-score>1:0</span>
                        <span data-away-team>Ротор</span>
                        <span data-status>завершен</span>
                    </div>
                </section>
            </body>
        </html>
        """
        next_round_html = """
        <html>
            <body data-current-round="10">
                <h1>ФНЛ 2026/2027</h1>
                <section>
                    <h2>10-й тур</h2>
                    <div data-match>
                        <span data-match-date>05.09.2026</span>
                        <span data-match-time>17:00</span>
                        <span data-home-team>КАМАЗ</span>
                        <span data-score></span>
                        <span data-away-team>Урал</span>
                        <span data-status>анонс</span>
                    </div>
                </section>
            </body>
        </html>
        """
        client = FakePageClient(
            pages_by_url={
                league_url: FetchedPage(url=league_url, html=league_html, status_code=200),
                next_round_url: FetchedPage(url=next_round_url, html=next_round_html, status_code=200),
            }
        )
        repository = FakeFootballDataRepository()
        service = LeagueSyncService(
            page_client=client,
            parser=KulichkiParser(base_url="https://football.kulichki.net"),
            repository=repository,
            league_sources=(LeagueSource(code="fnl", name="Россия", url=league_url),),
        )

        result = await service.sync_league("fnl")

        self.assertEqual(result.status, "success")
        self.assertEqual(result.parsed_matches, 2)
        self.assertEqual(client.fetched_urls, [league_url, next_round_url])
        self.assertEqual([round_.number for round_ in repository.saved_pages[0].rounds], [9, 10])

    async def test_sync_league_enriches_finished_matches_with_goal_events(self) -> None:
        league_html = _read_fixture("spain_league_live.html")
        match_url = "https://football.kulichki.net/spain/2027/1/4-Valensija-Betis-obzor-matcha-spain-2027.htm"
        client = FakePageClient(
            pages_by_url={
                "https://football.kulichki.net/spain/": FetchedPage(
                    url="https://football.kulichki.net/spain/",
                    html=league_html,
                    status_code=200,
                ),
                match_url: FetchedPage(
                    url=match_url,
                    html=_read_fixture("spain_match_review_live.html"),
                    status_code=200,
                ),
            }
        )
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

        self.assertEqual(result.status, "success")
        self.assertIn(match_url, client.fetched_urls)
        saved_matches = [
            match
            for round_ in repository.saved_pages[0].rounds
            for match in round_.matches
            if match.source_url == match_url
        ]
        self.assertEqual(len(saved_matches), 1)
        self.assertTrue(saved_matches[0].goal_events_loaded)
        self.assertEqual([event.scorer_name for event in saved_matches[0].goal_events], ["Рафинья", "Фермин Лопес"])

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

    def test_normalize_team_name_strips_country_suffix(self) -> None:
        self.assertEqual(normalize_team_name("Ливерпуль (Англия)"), "ливерпуль")
        self.assertEqual(normalize_team_name("  Атлетико   (Испания)  "), "атлетико")


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")

if __name__ == "__main__":
    unittest.main()
