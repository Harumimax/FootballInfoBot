from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol

from app.parser.dto import ParsedRound
from app.services.subscriptions.dto import (
    CurrentRoundView,
    LeagueView,
    StandingTableView,
    SubscriptionToggleResult,
    TelegramUserProfile,
)
from app.storage.repositories import FootballDataSqlAlchemyRepository
from app.storage.session import Database


class UserDataRepository(Protocol):
    async def upsert_telegram_user(self, profile: TelegramUserProfile) -> None:
        pass

    async def list_user_subscriptions(self, telegram_user_id: int) -> tuple[LeagueView, ...]:
        pass

    async def list_user_subscription_codes(self, telegram_user_id: int) -> frozenset[str]:
        pass

    async def toggle_league_subscription(
        self,
        *,
        telegram_user_id: int,
        league_code: str,
    ) -> tuple[LeagueView, bool]:
        pass

    async def get_current_round(self, league_code: str) -> CurrentRoundView | None:
        pass

    async def get_latest_standings(self, league_code: str) -> StandingTableView | None:
        pass


class FootballUserService:
    def __init__(self, repository: UserDataRepository) -> None:
        self._repository = repository

    async def register_user(self, profile: TelegramUserProfile) -> None:
        await self._repository.upsert_telegram_user(profile)

    async def get_subscription_codes(self, telegram_user_id: int) -> frozenset[str]:
        return await self._repository.list_user_subscription_codes(telegram_user_id)

    async def get_subscriptions(self, telegram_user_id: int) -> tuple[LeagueView, ...]:
        return await self._repository.list_user_subscriptions(telegram_user_id)

    async def toggle_subscription(
        self,
        *,
        telegram_user_id: int,
        league_code: str,
    ) -> SubscriptionToggleResult:
        league, is_active = await self._repository.toggle_league_subscription(
            telegram_user_id=telegram_user_id,
            league_code=league_code,
        )
        current_round: ParsedRound | None = None
        if is_active:
            round_view = await self._repository.get_current_round(league_code)
            current_round = round_view.round if round_view is not None else None
        return SubscriptionToggleResult(league=league, is_active=is_active, current_round=current_round)

    async def get_current_round(self, league_code: str) -> CurrentRoundView | None:
        return await self._repository.get_current_round(league_code)

    async def get_latest_standings(self, league_code: str) -> StandingTableView | None:
        return await self._repository.get_latest_standings(league_code)


class DatabaseFootballUserService:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def dispose(self) -> None:
        await self._database.dispose()

    def _service(self) -> AbstractAsyncContextManager[FootballUserService]:
        return _service_context(self._database)

    async def register_user(self, profile: TelegramUserProfile) -> None:
        async with self._service() as service:
            await service.register_user(profile)

    async def get_subscription_codes(self, telegram_user_id: int) -> frozenset[str]:
        async with self._service() as service:
            return await service.get_subscription_codes(telegram_user_id)

    async def get_subscriptions(self, telegram_user_id: int) -> tuple[LeagueView, ...]:
        async with self._service() as service:
            return await service.get_subscriptions(telegram_user_id)

    async def toggle_subscription(
        self,
        *,
        telegram_user_id: int,
        league_code: str,
    ) -> SubscriptionToggleResult:
        async with self._service() as service:
            return await service.toggle_subscription(telegram_user_id=telegram_user_id, league_code=league_code)

    async def get_current_round(self, league_code: str) -> CurrentRoundView | None:
        async with self._service() as service:
            return await service.get_current_round(league_code)

    async def get_latest_standings(self, league_code: str) -> StandingTableView | None:
        async with self._service() as service:
            return await service.get_latest_standings(league_code)

@asynccontextmanager
async def _service_context(database: Database) -> AsyncIterator[FootballUserService]:
    async with database.session() as session:
        yield FootballUserService(FootballDataSqlAlchemyRepository(session))
