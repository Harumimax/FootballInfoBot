from __future__ import annotations

import unittest

from app.config import Settings
from app.services.updates.factory import build_mvp_league_sources


class UpdateFactoryTest(unittest.TestCase):
    def test_build_mvp_league_sources_uses_configured_base_url(self) -> None:
        settings = Settings(
            telegram_bot_token="",
            database_url="postgresql+asyncpg://user:password@postgres:5432/football_bot",
            admin_user_ids=frozenset(),
            app_env="test",
            log_level="INFO",
            timezone="Europe/Moscow",
            kulichki_base_url="https://football.kulichki.net",
            kulichki_user_agent="FootballInfoBot/test",
        )

        sources = build_mvp_league_sources(settings)

        self.assertEqual(
            [source.code for source in sources],
            ["england", "spain", "germany", "italy", "france", "ruschamp"],
        )
        self.assertEqual(
            [source.name for source in sources],
            ["Англия", "Испания", "Германия", "Италия", "Франция", "Россия"],
        )
        self.assertEqual(sources[0].url, "https://football.kulichki.net/england/")
        self.assertEqual(sources[1].url, "https://football.kulichki.net/spain/")
        self.assertEqual(sources[2].url, "https://football.kulichki.net/germany/")
        self.assertEqual(sources[3].url, "https://football.kulichki.net/italy/")
        self.assertEqual(sources[4].url, "https://football.kulichki.net/france/")
        self.assertEqual(sources[5].url, "https://football.kulichki.net/ruschamp/")


if __name__ == "__main__":
    unittest.main()
