from __future__ import annotations

import unittest
from datetime import datetime

from app.parser.dto import LeaguePageData, ParsedLeague, ParsedMatch, ParsedRound, ParsedStandingRow
from app.storage.models import Round, StandingRow
from app.storage.repositories import FootballDataSqlAlchemyRepository


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self._next_id = 1
        self.flush_count = 0

    async def scalar(self, statement: object) -> None:
        return None

    def add(self, entity: object) -> None:
        self.added.append(entity)

    async def flush(self) -> None:
        self.flush_count += 1
        for entity in self.added:
            if getattr(entity, "id", None) is None:
                setattr(entity, "id", self._next_id)
                self._next_id += 1


class FootballDataSqlAlchemyRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_save_league_page_data_persists_all_visible_rounds(self) -> None:
        session = FakeAsyncSession()
        repository = FootballDataSqlAlchemyRepository(session)
        data = LeaguePageData(
            league=ParsedLeague(code="spain", name="Испания", source_url="https://football.kulichki.net/spain/"),
            season_label="2026/2027",
            source_season_key="2027",
            current_round=ParsedRound(
                number=3,
                source_url="https://football.kulichki.net/spain/2027/3/",
                matches=(
                    ParsedMatch(
                        home_team="Расинг",
                        away_team="Эльче",
                        scheduled_at=datetime(2026, 8, 28, 20, 0),
                        home_score=None,
                        away_score=None,
                        status="scheduled",
                        source_url="https://football.kulichki.net/spain/2027/3/6a-Rasing-Elche-anons-matcha-spain-2027.htm",
                    ),
                ),
            ),
            standings=(),
            rounds=(
                ParsedRound(
                    number=3,
                    source_url="https://football.kulichki.net/spain/2027/3/",
                    matches=(
                        ParsedMatch(
                            home_team="Расинг",
                            away_team="Эльче",
                            scheduled_at=datetime(2026, 8, 28, 20, 0),
                            home_score=None,
                            away_score=None,
                            status="scheduled",
                            source_url="https://football.kulichki.net/spain/2027/3/6a-Rasing-Elche-anons-matcha-spain-2027.htm",
                        ),
                    ),
                ),
                ParsedRound(
                    number=1,
                    source_url="https://football.kulichki.net/spain/2027/1/",
                    matches=(
                        ParsedMatch(
                            home_team="Барселона",
                            away_team="Атлетик",
                            scheduled_at=datetime(2026, 8, 27, 22, 0),
                            home_score=None,
                            away_score=None,
                            status="scheduled",
                            source_url="https://football.kulichki.net/spain/2027/1/3a-Barselona-Atletik-anons-matcha-spain-2027.htm",
                        ),
                    ),
                ),
            ),
        )

        result = await repository.save_league_page_data(data)

        added_rounds = [entity for entity in session.added if isinstance(entity, Round)]
        self.assertEqual([round_.round_number for round_ in added_rounds], [3, 1])
        self.assertEqual([round_.status for round_ in added_rounds], ["active", "planned"])
        self.assertEqual(result.created_matches, 2)
        self.assertEqual(result.created_change_events, 2)

    async def test_save_league_page_data_persists_standing_details(self) -> None:
        session = FakeAsyncSession()
        repository = FootballDataSqlAlchemyRepository(session)
        data = LeaguePageData(
            league=ParsedLeague(code="spain", name="Испания", source_url="https://football.kulichki.net/spain/"),
            season_label="2026/2027",
            source_season_key="2027",
            current_round=None,
            standings=(
                ParsedStandingRow(
                    position=1,
                    team_name="Реал Мадрид",
                    played=2,
                    wins=2,
                    draws=0,
                    losses=0,
                    goals_for=6,
                    goals_against=2,
                    goal_difference=4,
                    points=6,
                ),
            ),
        )

        await repository.save_league_page_data(data)

        added_standing_rows = [entity for entity in session.added if isinstance(entity, StandingRow)]
        self.assertEqual(len(added_standing_rows), 1)
        standing_row = added_standing_rows[0]
        self.assertEqual(standing_row.played, 2)
        self.assertEqual(standing_row.wins, 2)
        self.assertEqual(standing_row.draws, 0)
        self.assertEqual(standing_row.losses, 0)
        self.assertEqual(standing_row.goals_for, 6)
        self.assertEqual(standing_row.goals_against, 2)
        self.assertEqual(standing_row.goal_difference, 4)
        self.assertEqual(standing_row.points, 6)


if __name__ == "__main__":
    unittest.main()
