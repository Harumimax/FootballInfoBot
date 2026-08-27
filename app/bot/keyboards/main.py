from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.bot.messages import LeagueView, MVP_LEAGUES


MENU_MY_SUBSCRIPTIONS = "Мои подписки"
MENU_SUBSCRIBE = "Подписаться на лигу или турнир"
MENU_STANDINGS = "Турнирная таблица"
MENU_CURRENT_ROUND = "Текущий тур"
MENU_HELP = "Помощь"
MENU_ADMIN = "Админка"

CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX = "subscription:toggle:"
CALLBACK_TABLE_PREFIX = "table:"
CALLBACK_CURRENT_ROUND_PREFIX = "round:"


def build_main_menu_keyboard(*, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=MENU_MY_SUBSCRIPTIONS)],
        [KeyboardButton(text=MENU_SUBSCRIBE)],
        [KeyboardButton(text=MENU_STANDINGS), KeyboardButton(text=MENU_CURRENT_ROUND)],
        [KeyboardButton(text=MENU_HELP)],
    ]

    if is_admin:
        rows.append([KeyboardButton(text=MENU_ADMIN)])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def build_subscription_keyboard(
    *,
    subscribed_league_codes: frozenset[str] = frozenset(),
    leagues: tuple[LeagueView, ...] = MVP_LEAGUES,
) -> InlineKeyboardMarkup:
    rows = []
    for league in leagues:
        marker = "✓ " if league.code in subscribed_league_codes else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{marker}{league.name}",
                    callback_data=f"{CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX}{league.code}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_table_league_keyboard(*, leagues: tuple[LeagueView, ...] = MVP_LEAGUES) -> InlineKeyboardMarkup:
    return _build_league_keyboard(prefix=CALLBACK_TABLE_PREFIX, leagues=leagues)


def build_current_round_league_keyboard(*, leagues: tuple[LeagueView, ...] = MVP_LEAGUES) -> InlineKeyboardMarkup:
    return _build_league_keyboard(prefix=CALLBACK_CURRENT_ROUND_PREFIX, leagues=leagues)


def _build_league_keyboard(*, prefix: str, leagues: tuple[LeagueView, ...]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=league.name, callback_data=f"{prefix}{league.code}")]
            for league in leagues
        ]
    )
