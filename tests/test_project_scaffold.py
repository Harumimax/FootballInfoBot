from __future__ import annotations

import unittest

from app.config import DEFAULT_KULICHKI_BASE_URL, parse_admin_user_ids
from app.parser.dto import LeaguePageData, ParsedLeague
from app.scheduler.jobs import registered_job_names


class ProjectScaffoldTest(unittest.TestCase):
    def test_parse_admin_user_ids_accepts_empty_value(self) -> None:
        self.assertEqual(parse_admin_user_ids(""), frozenset())

    def test_parse_admin_user_ids_accepts_comma_separated_values(self) -> None:
        self.assertEqual(parse_admin_user_ids("123, 456"), frozenset({123, 456}))

    def test_parse_admin_user_ids_rejects_invalid_value(self) -> None:
        with self.assertRaises(ValueError):
            parse_admin_user_ids("123,not-a-number")

    def test_parser_dto_keeps_parser_independent_from_storage(self) -> None:
        league = ParsedLeague(
            code="spain",
            name="Испания",
            source_url=f"{DEFAULT_KULICHKI_BASE_URL}/spain/",
        )
        data = LeaguePageData(
            league=league,
            season_label="2026/2027",
            source_season_key="2027",
            current_round=None,
            standings=(),
        )

        self.assertEqual(data.league.code, "spain")
        self.assertIsNone(data.current_round)

    def test_worker_job_names_document_mvp_scheduler_shape(self) -> None:
        self.assertEqual(
            registered_job_names(),
            (
                "daily_full_sync",
                "morning_push",
                "after_matchday_check",
                "cleanup",
            ),
        )


if __name__ == "__main__":
    unittest.main()
