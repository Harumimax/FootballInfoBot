from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import AsyncMock

from app.parser.dto import LeaguePageData, ParsedGoalEvent, ParsedLeague, ParsedMatch, ParsedRound, ParsedStandingRow
from app.storage.models import League, MatchGoalEvent, Round, StandingRow
from app.storage.repositories import FootballDataSqlAlchemyRepository
from app.storage.repositories.football import _filter_nearby_catch_up_rounds, _select_finished_active_rounds


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self._next_id = 1
        self.flush_count = 0
        self.executed_statements: list[object] = []

    async def scalar(self, statement: object) -> None:
        return None

    async def execute(self, statement: object) -> tuple:
        self.executed_statements.append(statement)
        return ()

    def add(self, entity: object) -> None:
        self.added.append(entity)

    async def flush(self) -> None:
        self.flush_count += 1
        for entity in self.added:
            if getattr(entity, "id", None) is None:
                setattr(entity, "id", self._next_id)
                self._next_id += 1


class FakeQuerySession:
    def __init__(self, scalar_result: object | None = None) -> None:
        self.scalar_result = scalar_result
        self.executed_statements: list[object] = []

    async def scalar(self, statement: object) -> object | None:
        return self.scalar_result

    async def execute(self, statement: object) -> tuple:
        self.executed_statements.append(statement)
        return ()


class FootballDataSqlAlchemyRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_was_notification_sent_builds_notification_log_query(self) -> None:
        session = FakeAsyncSession()
        repository = FootballDataSqlAlchemyRepository(session)

        self.assertFalse(await repository.was_notification_sent("morning:2026-08-30:spain:123"))

    async def test_get_active_team_subscribers_does_not_exclude_league_subscribers(self) -> None:
        session = FakeQuerySession(
            scalar_result=League(
                id=10,
                source="kulichki",
                code="spain",
                name="Испания",
                source_url="https://football.kulichki.net/spain/",
            )
        )
        repository = FootballDataSqlAlchemyRepository(session)

        subscribers = await repository.get_active_team_subscribers_for_league("spain")

        self.assertEqual(subscribers, ())
        self.assertEqual(len(session.executed_statements), 1)
        self.assertNotIn("NOT IN", str(session.executed_statements[0]).upper())
        self.assertNotIn("team_subscriptions.league_id =", str(session.executed_statements[0]))

    async def test_get_current_round_returns_upcoming_round_when_no_active_round_exists(self) -> None:
        session = FakeAsyncSession()
        repository = FootballDataSqlAlchemyRepository(session)
        league = League(
            id=10,
            source="kulichki",
            code="league",
            name="Лига чемпионов",
            source_url="https://football.kulichki.net/league/",
        )
        season = object()
        upcoming_round = ParsedRound(
            number=1,
            source_url="https://football.kulichki.net/league/2027/1/",
            matches=(
                ParsedMatch(
                    home_team="ПСЖ",
                    away_team="Бавария",
                    scheduled_at=datetime(2026, 9, 17, 22, 0),
                    home_score=None,
                    away_score=None,
                    status="scheduled",
                ),
            ),
        )
        repository._get_active_league_by_code = AsyncMock(return_value=league)  # type: ignore[method-assign]
        repository._get_current_season = AsyncMock(return_value=season)  # type: ignore[method-assign]
        repository._load_current_visible_rounds = AsyncMock(return_value=(upcoming_round,))  # type: ignore[method-assign]

        result = await repository.get_current_round("league")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.round, upcoming_round)
        self.assertEqual(result.rounds, (upcoming_round,))

    def test_select_finished_active_rounds_prefers_next_round(self) -> None:
        finished_round = ParsedRound(
            number=9,
            source_url="https://football.kulichki.net/fnl/2027/9/",
            matches=(
                ParsedMatch(
                    home_team="Арсенал",
                    away_team="Ротор",
                    scheduled_at=datetime(2026, 8, 30, 19, 0),
                    home_score=1,
                    away_score=0,
                    status="finished",
                ),
            ),
        )
        next_round = ParsedRound(
            number=10,
            source_url="https://football.kulichki.net/fnl/2027/10/",
            matches=(
                ParsedMatch(
                    home_team="КАМАЗ",
                    away_team="Урал",
                    scheduled_at=datetime(2026, 9, 5, 17, 0),
                    home_score=None,
                    away_score=None,
                    status="scheduled",
                ),
            ),
        )

        result = _select_finished_active_rounds((finished_round,), next_round)

        self.assertEqual(result, (next_round,))

    def test_filter_nearby_catch_up_rounds_keeps_only_rounds_near_active_dates(self) -> None:
        active_round = ParsedRound(
            number=1,
            source_url="https://football.kulichki.net/league/2027/1/",
            matches=(
                ParsedMatch(
                    home_team="Ливерпуль",
                    away_team="Атлетико",
                    scheduled_at=datetime(2026, 9, 8, 22, 0),
                    home_score=None,
                    away_score=None,
                    status="scheduled",
                ),
            ),
        )
        future_round = ParsedRound(
            number=2,
            source_url="https://football.kulichki.net/league/2027/2/",
            matches=(
                ParsedMatch(
                    home_team="ПСЖ",
                    away_team="Бавария",
                    scheduled_at=datetime(2026, 10, 13, 22, 0),
                    home_score=None,
                    away_score=None,
                    status="scheduled",
                ),
            ),
        )
        catch_up_round = ParsedRound(
            number=0,
            source_url="https://football.kulichki.net/league/2027/0/",
            matches=(
                ParsedMatch(
                    home_team="Реал",
                    away_team="Барселона",
                    scheduled_at=datetime(2026, 9, 6, 22, 0),
                    home_score=None,
                    away_score=None,
                    status="scheduled",
                ),
            ),
        )

        result = _filter_nearby_catch_up_rounds((active_round,), (future_round, catch_up_round))

        self.assertEqual(result, (catch_up_round,))


    async def test_save_league_page_data_deactivates_previous_active_rounds(self) -> None:
        session = FakeAsyncSession()
        repository = FootballDataSqlAlchemyRepository(session)
        data = LeaguePageData(
            league=ParsedLeague(code="fnl", name="Россия", source_url="https://football.kulichki.net/fnl/"),
            season_label="2026/2027",
            source_season_key="2027",
            current_round=ParsedRound(
                number=10,
                source_url="https://football.kulichki.net/fnl/2027/10/",
                matches=(),
            ),
            standings=(),
            rounds=(
                ParsedRound(
                    number=10,
                    source_url="https://football.kulichki.net/fnl/2027/10/",
                    matches=(),
                ),
            ),
        )

        await repository.save_league_page_data(data)

        update_statements = [statement for statement in session.executed_statements if "UPDATE rounds" in str(statement)]
        self.assertEqual(len(update_statements), 1)
        self.assertIn("rounds.round_number !=", str(update_statements[0]))

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

    async def test_save_league_page_data_skips_duplicate_standing_teams(self) -> None:
        session = FakeAsyncSession()
        repository = FootballDataSqlAlchemyRepository(session)
        data = LeaguePageData(
            league=ParsedLeague(code="league", name="Лига чемпионов", source_url="https://football.kulichki.net/league/"),
            season_label="2026/2027",
            source_season_key="2027",
            current_round=None,
            standings=(
                ParsedStandingRow(position=1, team_name="ПСЖ", played=0, points=0),
                ParsedStandingRow(position=1, team_name="ПСЖ", played=0, points=0),
            ),
        )

        await repository.save_league_page_data(data)

        added_standing_rows = [entity for entity in session.added if isinstance(entity, StandingRow)]
        self.assertEqual(len(added_standing_rows), 1)

    async def test_save_league_page_data_persists_goal_events(self) -> None:
        session = FakeAsyncSession()
        repository = FootballDataSqlAlchemyRepository(session)
        data = LeaguePageData(
            league=ParsedLeague(code="spain", name="Испания", source_url="https://football.kulichki.net/spain/"),
            season_label="2026/2027",
            source_season_key="2027",
            current_round=ParsedRound(
                number=1,
                source_url="https://football.kulichki.net/spain/2027/1/",
                matches=(
                    ParsedMatch(
                        home_team="Барселона",
                        away_team="Атлетик",
                        scheduled_at=datetime(2026, 8, 27, 22, 0),
                        home_score=3,
                        away_score=0,
                        status="finished",
                        source_url="https://football.kulichki.net/spain/2027/1/3-Barselona-Atletik-obzor-matcha-spain-2027.htm",
                        goal_events=(
                            ParsedGoalEvent(
                                minute="13",
                                scorer_name="Таррега",
                                score_after="1:0",
                                position=1,
                                is_own_goal=True,
                            ),
                            ParsedGoalEvent(minute="37", scorer_name="Рафинья", score_after="2:0", position=2),
                            ParsedGoalEvent(minute="82", scorer_name="Фермин Лопес", score_after="3:0", position=3),
                        ),
                        goal_events_loaded=True,
                    ),
                ),
            ),
            standings=(),
        )

        await repository.save_league_page_data(data)

        added_goal_events = [entity for entity in session.added if isinstance(entity, MatchGoalEvent)]
        self.assertEqual(len(added_goal_events), 3)
        self.assertEqual(added_goal_events[0].minute, "13")
        self.assertEqual(added_goal_events[0].scorer_name, "Таррега")
        self.assertEqual(added_goal_events[0].score_after, "1:0")
        self.assertTrue(added_goal_events[0].is_own_goal)
        self.assertEqual(added_goal_events[1].minute, "37")
        self.assertEqual(added_goal_events[1].scorer_name, "Рафинья")
        self.assertFalse(added_goal_events[1].is_own_goal)
        self.assertEqual(added_goal_events[2].minute, "82")
        self.assertEqual(added_goal_events[2].scorer_name, "Фермин Лопес")

if __name__ == "__main__":
    unittest.main()
