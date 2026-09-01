from __future__ import annotations

from aiogram import Bot

from app.bot.messages import USER_MESSAGE_PARSE_MODE
from app.services.notifications.push import PushNotification


class TelegramPushSender:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send(self, notification: PushNotification) -> None:
        await self._bot.send_message(
            chat_id=notification.telegram_user_id,
            text=notification.text,
            disable_web_page_preview=True,
            parse_mode=USER_MESSAGE_PARSE_MODE,
        )
