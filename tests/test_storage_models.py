from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from sqlalchemy import UniqueConstraint

from app.storage.models import Base, League, Match, MatchGoalEvent, NotificationLog, Subscription


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "leagues",
    "seasons",
    "teams",
    "rounds",
    "matches",
    "match_goal_events",
    "standings_snapshots",
    "standings_rows",
    "users",
    "subscriptions",
    "parser_runs",
    "data_change_events",
    "notification_log",
}


class StorageModelsTest(unittest.TestCase):
    def test_metadata_contains_mvp_tables(self) -> None:
        self.assertEqual(set(Base.metadata.tables), EXPECTED_TABLES)

    def test_league_has_source_code_identity(self) -> None:
        self.assertTrue(_has_unique_constraint(League, "source", "code"))

    def test_match_has_stable_source_round_team_identity(self) -> None:
        self.assertTrue(
            _has_unique_constraint(
                Match,
                "source",
                "league_id",
                "season_id",
                "round_id",
                "home_team_id",
                "away_team_id",
            )
        )

    def test_subscription_has_user_league_identity(self) -> None:
        self.assertTrue(_has_unique_constraint(Subscription, "user_id", "league_id"))

    def test_notification_log_has_dedupe_key_identity(self) -> None:
        self.assertTrue(_has_unique_constraint(NotificationLog, "dedupe_key"))

    def test_match_goal_event_has_match_position_identity(self) -> None:
        self.assertTrue(_has_unique_constraint(MatchGoalEvent, "match_id", "position"))

    def test_initial_migration_seeds_mvp_leagues(self) -> None:
        migration = PROJECT_ROOT / "migrations" / "versions" / "202608270001_initial_schema.py"
        migration_text = migration.read_text(encoding="utf-8")

        self.assertIn('"code": "england"', migration_text)
        self.assertIn('"name": "Англия"', migration_text)
        self.assertIn('"code": "spain"', migration_text)
        self.assertIn('"name": "Испания"', migration_text)
        self.assertNotIn("�", migration_text)

    def test_alembic_can_render_offline_upgrade_sql(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("CREATE TABLE leagues", result.stdout)
        self.assertIn("CREATE TABLE matches", result.stdout)
        self.assertIn("INSERT INTO leagues", result.stdout)

    def test_notification_dedupe_migration_adds_key(self) -> None:
        migration = PROJECT_ROOT / "migrations" / "versions" / "202608270002_add_notification_dedupe_key.py"
        migration_text = migration.read_text(encoding="utf-8")

        self.assertIn("dedupe_key", migration_text)
        self.assertIn("uq_notification_log_dedupe_key", migration_text)


def _has_unique_constraint(model: type[object], *column_names: str) -> bool:
    expected = set(column_names)
    return any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns} == expected
        for constraint in model.__table__.constraints
    )


if __name__ == "__main__":
    unittest.main()
