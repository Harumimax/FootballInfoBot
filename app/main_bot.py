from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app.bot.dispatcher import create_dispatcher
from app.config import load_settings
from app.services.subscriptions.user_service import DatabaseFootballUserService
from app.storage.session import Database


async def run_bot() -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger(__name__)

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is empty; bot polling is not started")
        return

    football_user_service = None
    if settings.database_url:
        football_user_service = DatabaseFootballUserService(Database(settings.database_url))
    else:
        logger.warning("DATABASE_URL is empty; live user data is disabled")

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = create_dispatcher(
        admin_user_ids=settings.admin_user_ids,
        football_user_service=football_user_service,
    )
    try:
        logger.info("Starting FootballInfoBot polling")
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
        if football_user_service is not None:
            await football_user_service.dispose()


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
