from __future__ import annotations

import unittest
import asyncio

from app.storage.session import DatabaseUrlError, create_engine, create_session_factory


class StorageSessionTest(unittest.TestCase):
    def test_create_engine_rejects_empty_database_url(self) -> None:
        with self.assertRaises(DatabaseUrlError):
            create_engine("")

    def test_create_session_factory_disables_expire_on_commit(self) -> None:
        engine = create_engine("postgresql+asyncpg://user:password@localhost:5432/football_bot")

        try:
            session_factory = create_session_factory(engine)

            self.assertFalse(session_factory.kw["expire_on_commit"])
        finally:
            asyncio.run(engine.dispose())


if __name__ == "__main__":
    unittest.main()
