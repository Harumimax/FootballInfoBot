from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config import Settings
from app.parser.clients.http import HttpPageClient
from app.parser.kulichki import KulichkiParser
from app.services.updates.sync import LeagueSource, LeagueSyncService
from app.storage.repositories import FootballDataSqlAlchemyRepository
from app.storage.session import Database


MVP_LEAGUE_CODES = ("england", "spain", "germany", "italy", "france")
MVP_LEAGUE_NAMES = {
    "england": "Англия",
    "spain": "Испания",
    "germany": "Германия",
    "italy": "Италия",
    "france": "Франция",
}


def build_mvp_league_sources(settings: Settings) -> tuple[LeagueSource, ...]:
    return tuple(
        LeagueSource(
            code=league_code,
            name=MVP_LEAGUE_NAMES[league_code],
            url=f"{settings.kulichki_base_url}/{league_code}/",
        )
        for league_code in MVP_LEAGUE_CODES
    )


@asynccontextmanager
async def create_league_sync_service(settings: Settings) -> AsyncIterator[LeagueSyncService]:
    database = Database(settings.database_url)
    try:
        async with database.session() as session:
            yield LeagueSyncService(
                page_client=HttpPageClient(user_agent=settings.kulichki_user_agent),
                parser=KulichkiParser(base_url=settings.kulichki_base_url),
                repository=FootballDataSqlAlchemyRepository(session),
                league_sources=build_mvp_league_sources(settings),
            )
    finally:
        await database.dispose()
