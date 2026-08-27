from __future__ import annotations

from aiogram import Dispatcher

from app.bot.handlers.admin import create_admin_router
from app.bot.handlers.start import create_start_router
from app.services.subscriptions.user_service import FootballUserService


def create_dispatcher(
    *,
    admin_user_ids: frozenset[int],
    football_user_service: FootballUserService | None = None,
) -> Dispatcher:
    dispatcher = Dispatcher(admin_user_ids=admin_user_ids, football_user_service=football_user_service)
    dispatcher.include_router(create_admin_router())
    dispatcher.include_router(create_start_router())
    return dispatcher
