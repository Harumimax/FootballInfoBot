from __future__ import annotations

import unittest
import asyncio

from app.config import Settings
from app.scheduler.jobs import daily_full_sync_job_specs
from app.scheduler.runner import WorkerRuntime, build_scheduler


class SchedulerRunnerTest(unittest.TestCase):
    def test_daily_full_sync_job_specs_document_schedule(self) -> None:
        specs = daily_full_sync_job_specs()

        self.assertEqual(
            [(spec.name, spec.hour, spec.minute) for spec in specs],
            [
                ("daily_full_sync", 6, 0),
                ("daily_full_sync", 18, 0),
            ],
        )

    def test_build_scheduler_registers_sync_push_and_cleanup_jobs(self) -> None:
        runtime = WorkerRuntime(settings=_settings())
        scheduler = build_scheduler(runtime, timezone="Europe/Moscow")

        try:
            job_ids = sorted(job.id for job in scheduler.get_jobs())

            self.assertEqual(
                job_ids,
                [
                    "after_matchday_check_00_00",
                    "after_matchday_check_01_00",
                    "after_matchday_check_02_00",
                    "after_matchday_check_03_00",
                    "after_matchday_check_23_00",
                    "cleanup_04_00",
                    "daily_full_sync_06_00",
                    "daily_full_sync_18_00",
                    "morning_push_09_00",
                ],
            )
        finally:
            asyncio.run(runtime.dispose())


def _settings() -> Settings:
    return Settings(
        telegram_bot_token="",
        database_url="postgresql+asyncpg://user:password@postgres:5432/football_bot",
        admin_user_ids=frozenset(),
        app_env="test",
        log_level="INFO",
        timezone="Europe/Moscow",
        kulichki_base_url="https://football.kulichki.net",
        kulichki_user_agent="FootballInfoBot/test",
    )


if __name__ == "__main__":
    unittest.main()
