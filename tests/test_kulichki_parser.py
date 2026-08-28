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

    def test_parse_live_league_page_extracts_real_kulichki_markup(self) -> None:
        html = _read_fixture("england_league_live.html")

        data = self.parser.parse_league_page(
            html,
            url="https://football.kulichki.net/england/",
            league_code="england",
            league_name="Англия",
        )

        self.assertEqual(data.season_label, "2026/2027")
        self.assertEqual(data.source_season_key, "2027")
        self.assertIsNotNone(data.current_round)
        assert data.current_round is not None
        self.assertEqual(data.current_round.number, 2)
        self.assertEqual(data.current_round.source_url, "https://football.kulichki.net/england/2027/2/")
        self.assertEqual(len(data.current_round.matches), 10)
        self.assertEqual(len(data.standings), 20)

        first_match = data.current_round.matches[0]
        self.assertEqual(first_match.home_team, "Кристал Пэлас")
        self.assertEqual(first_match.away_team, "Манчестер Сити")
        self.assertIsNotNone(first_match.scheduled_at)
        assert first_match.scheduled_at is not None
        self.assertEqual(first_match.scheduled_at.strftime("%Y-%m-%d %H:%M"), "2026-08-28 22:00")
        self.assertIsNone(first_match.home_score)
        self.assertIsNone(first_match.away_score)
        self.assertEqual(first_match.status, "scheduled")
        self.assertEqual(
            first_match.source_url,
            "https://football.kulichki.net/england/2027/2/4a-Kristal-Pelas-Manchester-Siti-anons-matcha-england-2027.htm",
        )

        self.assertEqual(data.standings[0].team_name, "Брайтон")
        self.assertEqual(data.standings[0].played, 1)
        self.assertEqual(data.standings[0].wins, 1)
        self.assertEqual(data.standings[0].draws, 0)
        self.assertEqual(data.standings[0].losses, 0)
        self.assertEqual(data.standings[0].goals_for, 4)
        self.assertEqual(data.standings[0].goals_against, 0)
        self.assertEqual(data.standings[0].goal_difference, 4)
        self.assertEqual(data.standings[0].points, 3)

    def test_parse_live_round_page_extracts_finished_matches_without_time(self) -> None:
        html = _read_fixture("spain_round_live.html")

        data = self.parser.parse_round_page(
            html,
            url="https://football.kulichki.net/spain/2027/2/",
            league_code="spain",
            league_name="Испания",
        )

        self.assertEqual(data.season_label, "2026/2027")
        self.assertEqual(data.round.number, 2)
        self.assertEqual(len(data.round.matches), 10)

        first_match = data.round.matches[0]
        self.assertEqual(first_match.home_team, "Райо Вальекано")
        self.assertEqual(first_match.away_team, "Алавес")
        self.assertIsNotNone(first_match.scheduled_at)
        assert first_match.scheduled_at is not None
        self.assertEqual(first_match.scheduled_at.strftime("%Y-%m-%d %H:%M"), "2026-08-20 00:00")
        self.assertEqual(first_match.home_score, 1)
        self.assertEqual(first_match.away_score, 1)
        self.assertEqual(first_match.status, "finished")
        self.assertEqual(
            first_match.source_url,
            "https://football.kulichki.net/spain/2027/2/7-Rajo-Valekano-Alaves-obzor-matcha-spain-2027.htm",
        )

    def test_parse_live_league_page_groups_current_and_catch_up_rounds(self) -> None:
        html = _read_fixture("spain_league_live.html")

        data = self.parser.parse_league_page(
            html,
            url="https://football.kulichki.net/spain/",
            league_code="spain",
            league_name="Испания",
        )

        self.assertIsNotNone(data.current_round)
        assert data.current_round is not None
        self.assertEqual(data.current_round.number, 3)
        self.assertEqual(data.current_round.source_url, "https://football.kulichki.net/spain/2027/3/")
        self.assertEqual(len(data.current_round.matches), 10)
        self.assertTrue(all("/spain/2027/3/" in (match.source_url or "") for match in data.current_round.matches))
        self.assertEqual(data.current_round.matches[-1].home_team, "Барселона")
        self.assertEqual(data.current_round.matches[-1].away_team, "Райо Вальекано")
        self.assertEqual(data.current_round.matches[-1].scheduled_at.strftime("%Y-%m-%d %H:%M"), "2026-08-31 22:30")

        self.assertEqual([round_.number for round_ in data.rounds], [3, 1])
        catch_up_round = data.rounds[1]
        self.assertEqual(catch_up_round.source_url, "https://football.kulichki.net/spain/2027/1/")
        self.assertEqual(len(catch_up_round.matches), 4)
        self.assertTrue(all("/spain/2027/1/" in (match.source_url or "") for match in catch_up_round.matches))
        self.assertEqual(catch_up_round.matches[-1].home_team, "Барселона")
        self.assertEqual(catch_up_round.matches[-1].away_team, "Атлетик")

        first_standing = data.standings[0]
        self.assertEqual(first_standing.team_name, "Реал Мадрид")
        self.assertEqual(first_standing.played, 2)
        self.assertEqual(first_standing.wins, 2)
        self.assertEqual(first_standing.draws, 0)
        self.assertEqual(first_standing.losses, 0)
        self.assertEqual(first_standing.goals_for, 6)
        self.assertEqual(first_standing.goals_against, 2)
        self.assertEqual(first_standing.goal_difference, 4)
        self.assertEqual(first_standing.points, 6)

    def test_parse_match_page_extracts_goal_events_from_review(self) -> None:
        html = _read_fixture("spain_match_review_live.html")

        goals = self.parser.parse_match_page(
            html,
            url="https://football.kulichki.net/spain/2027/1/3-Barselona-Atletik-obzor-matcha-spain-2027.htm",
        )

        self.assertEqual(len(goals), 2)
        self.assertEqual(goals[0].minute, "37")
        self.assertEqual(goals[0].scorer_name, "Рафинья")
        self.assertEqual(goals[0].score_after, "1:0")
        self.assertEqual(goals[0].position, 1)
        self.assertEqual(goals[1].minute, "82")
        self.assertEqual(goals[1].scorer_name, "Фермин Лопес")
        self.assertEqual(goals[1].score_after, "2:0")


def _read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
