from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.scheduler.jobs import daily_full_sync_job_specs, mvp_push_job_specs
from app.services.notifications import PushNotificationService, TelegramPushSender
from app.services.updates.factory import build_mvp_league_sources, create_league_sync_service
from app.storage.repositories import FootballDataSqlAlchemyRepository
from app.storage.session import Database


logger = logging.getLogger(__name__)


class WorkerRuntime:
    def __init__(self, *, settings: Settings, bot: Bot | None = None) -> None:
        self._settings = settings
        self._database = Database(settings.database_url)
        self._bot = bot

    async def dispose(self) -> None:
        if self._bot is not None:
            await self._bot.session.close()
        await self._database.dispose()

    async def sync_all_leagues(self) -> None:
        async with create_league_sync_service(self._settings) as service:
            for league in build_mvp_league_sources(self._settings):
                result = await service.sync_league(league.code)
                logger.info(
                    "Synced league %s: status=%s matches=%s standings=%s",
                    result.league_code,
                    result.status,
                    result.parsed_matches,
                    result.parsed_standings_rows,
                )

    async def send_morning_pushes(self) -> None:
        await self.sync_all_leagues()
        if self._bot is None:
            logger.warning("TELEGRAM_BOT_TOKEN is empty; morning push is skipped")
            return

        async with self._database.session() as session:
            service = PushNotificationService(
                repository=FootballDataSqlAlchemyRepository(session),
                sender=TelegramPushSender(self._bot),
            )
            result = await service.send_morning_pushes(datetime.now(self._settings.tzinfo))
            logger.info("Morning push finished: sent=%s skipped=%s", result.sent_count, result.skipped_leagues)

    async def check_after_matchday_pushes(self) -> None:
        await self.sync_all_leagues()
        if self._bot is None:
            logger.warning("TELEGRAM_BOT_TOKEN is empty; after-matchday push is skipped")
            return

        async with self._database.session() as session:
            service = PushNotificationService(
                repository=FootballDataSqlAlchemyRepository(session),
                sender=TelegramPushSender(self._bot),
            )
            result = await service.check_after_matchday_pushes(datetime.now(self._settings.tzinfo))
            logger.info(
                "After-matchday check finished: sent=%s skipped=%s pending=%s",
                result.sent_count,
                result.skipped_leagues,
                result.pending_leagues,
            )

    async def cleanup(self) -> None:
        logger.info("Cleanup job is not implemented yet")


def build_scheduler(runtime: WorkerRuntime, *, timezone: str) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=timezone)

    for spec in daily_full_sync_job_specs():
        scheduler.add_job(
            runtime.sync_all_leagues,
            CronTrigger(hour=spec.hour, minute=spec.minute, timezone=timezone),
            id=f"{spec.name}_{spec.hour:02d}_{spec.minute:02d}",
            replace_existing=True,
        )

    for spec in mvp_push_job_specs():
        job = runtime.send_morning_pushes if spec.name == "morning_push" else runtime.check_after_matchday_pushes
        scheduler.add_job(
            job,
            CronTrigger(hour=spec.hour, minute=spec.minute, timezone=timezone),
            id=f"{spec.name}_{spec.hour:02d}_{spec.minute:02d}",
            replace_existing=True,
        )

    scheduler.add_job(
        runtime.cleanup,
        CronTrigger(hour=4, minute=0, timezone=timezone),
        id="cleanup_04_00",
        replace_existing=True,
    )
    return scheduler


async def run_worker(settings: Settings) -> None:
    logging.basicConfig(level=settings.log_level)
    bot = Bot(token=settings.telegram_bot_token) if settings.telegram_bot_token else None
    runtime = WorkerRuntime(settings=settings, bot=bot)
    scheduler = build_scheduler(runtime, timezone=settings.timezone)

    try:
        scheduler.start()
        logger.info("FootballInfoBot worker started")
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)
        await runtime.dispose()
