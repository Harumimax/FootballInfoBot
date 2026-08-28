from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.messages import LeagueView, MVP_LEAGUES


CALLBACK_ADMIN_SYNC_MENU = "admin:sync_menu"
CALLBACK_ADMIN_STATUS = "admin:status"
CALLBACK_ADMIN_LAST_ERROR = "admin:last_error"
CALLBACK_ADMIN_TOGGLE_MENU = "admin:toggle_menu"
CALLBACK_ADMIN_SUBSCRIBERS = "admin:subscribers"
CALLBACK_ADMIN_NOTIFICATIONS = "admin:notifications"
CALLBACK_ADMIN_TEAMS_MENU = "admin:teams_menu"
CALLBACK_ADMIN_TEST_PUSH = "admin:test_push"
CALLBACK_ADMIN_SYNC_PREFIX = "admin:sync:"
CALLBACK_ADMIN_TOGGLE_PREFIX = "admin:toggle:"
CALLBACK_ADMIN_TEAMS_PREFIX = "admin:teams:"


def build_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Обновить лигу", callback_data=CALLBACK_ADMIN_SYNC_MENU)],
            [InlineKeyboardButton(text="Статус парсера", callback_data=CALLBACK_ADMIN_STATUS)],
            [InlineKeyboardButton(text="Последняя ошибка", callback_data=CALLBACK_ADMIN_LAST_ERROR)],
            [InlineKeyboardButton(text="Включить/отключить лигу", callback_data=CALLBACK_ADMIN_TOGGLE_MENU)],
            [InlineKeyboardButton(text="Активные подписки", callback_data=CALLBACK_ADMIN_SUBSCRIBERS)],
            [InlineKeyboardButton(text="Последние уведомления", callback_data=CALLBACK_ADMIN_NOTIFICATIONS)],
            [InlineKeyboardButton(text="Команды лиги", callback_data=CALLBACK_ADMIN_TEAMS_MENU)],
            [InlineKeyboardButton(text="Тестовый пуш себе", callback_data=CALLBACK_ADMIN_TEST_PUSH)],
        ]
    )


def build_admin_sync_league_keyboard(*, leagues: tuple[LeagueView, ...] = MVP_LEAGUES) -> InlineKeyboardMarkup:
    return _build_admin_league_keyboard(prefix=CALLBACK_ADMIN_SYNC_PREFIX, leagues=leagues)


def build_admin_toggle_league_keyboard(*, leagues: tuple[LeagueView, ...] = MVP_LEAGUES) -> InlineKeyboardMarkup:
    return _build_admin_league_keyboard(prefix=CALLBACK_ADMIN_TOGGLE_PREFIX, leagues=leagues)


def build_admin_teams_league_keyboard(*, leagues: tuple[LeagueView, ...] = MVP_LEAGUES) -> InlineKeyboardMarkup:
    return _build_admin_league_keyboard(prefix=CALLBACK_ADMIN_TEAMS_PREFIX, leagues=leagues)


def _build_admin_league_keyboard(*, prefix: str, leagues: tuple[LeagueView, ...]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=league.name, callback_data=f"{prefix}{league.code}")]
            for league in leagues
        ]
    )
