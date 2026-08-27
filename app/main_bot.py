from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app.bot.dispatcher import create_dispatcher
from app.config import load_settings


async def run_bot() -> None:
    settings = load_settings()
    logging.basicConfig(level=settings.log_level)
    logger = logging.getLogger(__name__)

    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is empty; bot polling is not started")
        return

    bot = Bot(token=settings.telegram_bot_token)
    dispatcher = create_dispatcher(admin_user_ids=settings.admin_user_ids)
    logger.info("Starting FootballInfoBot polling")
    await dispatcher.start_polling(bot)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
