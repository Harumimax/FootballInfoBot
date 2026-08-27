from __future__ import annotations

from aiogram import Dispatcher

from app.bot.handlers.start import router as start_router


def create_dispatcher(*, admin_user_ids: frozenset[int]) -> Dispatcher:
    dispatcher = Dispatcher(admin_user_ids=admin_user_ids)
    dispatcher.include_router(start_router)
    return dispatcher
