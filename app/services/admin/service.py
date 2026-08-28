from __future__ import annotations

from typing import Protocol

from app.config import Settings
from app.services.admin.dto import (
    AdminSubscriptionStatsView,
    AdminSyncResult,
    AdminTeamListView,
    LeagueToggleResult,
    ParserStatusView,
    RecentNotificationView,
)
from app.services.subscriptions.dto import LeagueView
from app.services.updates.factory import build_mvp_league_sources, create_league_sync_service
from app.storage.repositories import FootballDataSqlAlchemyRepository
from app.storage.session import Database


class AdminDataRepository(Protocol):
    async def get_parser_status(self) -> ParserStatusView:
        pass

    async def get_last_parser_error(self) -> str | None:
        pass

    async def toggle_league_active(self, league_code: str) -> LeagueToggleResult:
        pass

    async def get_subscription_stats(self) -> AdminSubscriptionStatsView:
        pass

    async def get_recent_notifications(self, limit: int = 10) -> tuple[RecentNotificationView, ...]:
        pass

    async def get_league_teams(self, league_code: str) -> AdminTeamListView | None:
        pass


class FootballAdminService:
    def __init__(self, *, settings: Settings, database: Database) -> None:
        self._settings = settings
        self._database = database

    async def dispose(self) -> None:
        await self._database.dispose()

    async def sync_league(self, league_code: str) -> AdminSyncResult:
        league_name = _league_name_by_code(league_code, self._settings)
        async with create_league_sync_service(self._settings) as service:
            result = await service.sync_league(league_code)
        return AdminSyncResult(
            league_name=league_name,
            status=result.status,
            parsed_matches=result.parsed_matches,
            parsed_standings_rows=result.parsed_standings_rows,
            error_message=result.error_message,
        )

    async def get_parser_status(self) -> ParserStatusView:
        async with self._database.session() as session:
            return await FootballDataSqlAlchemyRepository(session).get_parser_status()

    async def get_last_parser_error(self) -> str | None:
        async with self._database.session() as session:
            return await FootballDataSqlAlchemyRepository(session).get_last_parser_error()

    async def toggle_league_active(self, league_code: str) -> LeagueToggleResult:
        async with self._database.session() as session:
            return await FootballDataSqlAlchemyRepository(session).toggle_league_active(league_code)

    async def get_subscription_stats(self) -> AdminSubscriptionStatsView:
        async with self._database.session() as session:
            return await FootballDataSqlAlchemyRepository(session).get_subscription_stats()

    async def get_recent_notifications(self, limit: int = 10) -> tuple[RecentNotificationView, ...]:
        async with self._database.session() as session:
            return await FootballDataSqlAlchemyRepository(session).get_recent_notifications(limit=limit)

    async def get_league_teams(self, league_code: str) -> AdminTeamListView | None:
        league_name = _league_name_by_code(league_code, self._settings)
        async with self._database.session() as session:
            teams = await FootballDataSqlAlchemyRepository(session).list_league_teams(league_code)
        if not teams:
            return None
        return AdminTeamListView(league=LeagueView(code=league_code, name=league_name), teams=teams)


def _league_name_by_code(league_code: str, settings: Settings) -> str:
    for league in build_mvp_league_sources(settings):
        if league.code == league_code:
            return league.name
    return league_code
