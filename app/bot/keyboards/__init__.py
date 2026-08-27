"""Telegram keyboard builders."""

from app.bot.keyboards.main import (
    CALLBACK_CURRENT_ROUND_PREFIX,
    CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX,
    CALLBACK_TABLE_PREFIX,
    MENU_ADMIN,
    MENU_CURRENT_ROUND,
    MENU_HELP,
    MENU_MY_SUBSCRIPTIONS,
    MENU_STANDINGS,
    MENU_SUBSCRIBE,
    build_current_round_league_keyboard,
    build_main_menu_keyboard,
    build_subscription_keyboard,
    build_table_league_keyboard,
)

__all__ = [
    "CALLBACK_CURRENT_ROUND_PREFIX",
    "CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX",
    "CALLBACK_TABLE_PREFIX",
    "MENU_ADMIN",
    "MENU_CURRENT_ROUND",
    "MENU_HELP",
    "MENU_MY_SUBSCRIPTIONS",
    "MENU_STANDINGS",
    "MENU_SUBSCRIBE",
    "build_current_round_league_keyboard",
    "build_main_menu_keyboard",
    "build_subscription_keyboard",
    "build_table_league_keyboard",
]
