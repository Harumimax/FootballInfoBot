from __future__ import annotations

import unittest
from pathlib import Path

from app.parser.kulichki import KulichkiParser


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "kulichki"


class KulichkiParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = KulichkiParser(base_url="https://football.kulichki.net")

    def test_parse_league_page_extracts_current_round_matches_and_standings(self) -> None:
        html = _read_fixture("england_league.html")

        data = self.parser.parse_league_page(
            html,
            url="https://football.kulichki.net/england/",
            league_code="england",
            league_name="Англия",
        )

        self.assertEqual(data.league.code, "england")
        self.assertEqual(data.season_label, "2026/2027")
        self.assertEqual(data.source_season_key, "2027")
        self.assertIsNotNone(data.current_round)
        assert data.current_round is not None
        self.assertEqual(data.current_round.number, 1)
        self.assertEqual(data.current_round.source_url, "https://football.kulichki.net/england/2027/1/")
        self.assertEqual(len(data.current_round.matches), 2)

        finished_match = data.current_round.matches[0]
        self.assertEqual(finished_match.home_team, "Ливерпуль")
        self.assertEqual(finished_match.away_team, "Борнмут")
        self.assertEqual(finished_match.home_score, 4)
        self.assertEqual(finished_match.away_score, 2)
        self.assertEqual(finished_match.status, "finished")
        self.assertIsNotNone(finished_match.scheduled_at)
        assert finished_match.scheduled_at is not None
        self.assertEqual(finished_match.scheduled_at.strftime("%d.%m %H:%M"), "21.08 20:00")

        self.assertEqual(len(data.standings), 2)
        self.assertEqual(data.standings[0].team_name, "Ливерпуль")
        self.assertEqual(data.standings[0].points, 3)

    def test_parse_round_page_extracts_round_matches_from_table(self) -> None:
        html = _read_fixture("spain_round.html")

        data = self.parser.parse_round_page(
            html,
            url="https://football.kulichki.net/spain/2027/3/",
            league_code="spain",
            league_name="Испания",
        )

        self.assertEqual(data.league.source_url, "https://football.kulichki.net/spain/")
        self.assertEqual(data.round.number, 3)
        self.assertEqual(len(data.round.matches), 2)
        self.assertEqual(data.round.matches[0].home_team, "Реал")
        self.assertEqual(data.round.matches[0].away_team, "Барселона")
        self.assertEqual(data.round.matches[0].status, "scheduled")
        self.assertEqual(data.round.matches[1].home_score, 2)
        self.assertEqual(data.round.matches[1].away_score, 1)
        self.assertEqual(data.round.matches[1].status, "finished")


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
