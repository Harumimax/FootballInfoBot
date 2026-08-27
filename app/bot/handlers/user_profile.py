from __future__ import annotations

from aiogram.types import Message

from app.services.subscriptions.dto import TelegramUserProfile


def telegram_profile_from_message(message: Message) -> TelegramUserProfile:
    if message.from_user is None:
        raise ValueError("Telegram message has no from_user")

    user = message.from_user
    display_name = user.full_name or user.username or str(user.id)
    return TelegramUserProfile(
        telegram_user_id=user.id,
        username=user.username,
        display_name=display_name,
        language_code=user.language_code,
    )
