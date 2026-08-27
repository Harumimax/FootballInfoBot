from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    CALLBACK_CURRENT_ROUND_PREFIX,
    CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX,
    CALLBACK_TABLE_PREFIX,
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
from app.bot.messages import (
    MVP_LEAGUES,
    NO_DATA_MESSAGE,
    render_empty_subscriptions_message,
    render_group_not_supported_message,
    render_help_message,
    render_select_league_for_round_message,
    render_select_league_for_table_message,
    render_select_subscription_message,
    render_start_message,
)


async def handle_private_start(message: Message, admin_user_ids: frozenset[int] | None = None) -> None:
    await message.answer(
        render_start_message(),
        reply_markup=build_main_menu_keyboard(is_admin=_is_admin(message, admin_user_ids)),
    )


async def handle_private_help(message: Message) -> None:
    await message.answer(render_help_message())


async def handle_my_subscriptions(message: Message) -> None:
    await message.answer(render_empty_subscriptions_message(), reply_markup=build_subscription_keyboard())


async def handle_subscribe_menu(message: Message) -> None:
    await message.answer(render_select_subscription_message(), reply_markup=build_subscription_keyboard())


async def handle_standings_menu(message: Message) -> None:
    await message.answer(render_select_league_for_table_message(), reply_markup=build_table_league_keyboard())


async def handle_current_round_menu(message: Message) -> None:
    await message.answer(render_select_league_for_round_message(), reply_markup=build_current_round_league_keyboard())


async def handle_subscription_toggle(callback: CallbackQuery) -> None:
    league_code = _strip_callback_prefix(callback.data, CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX)
    league_name = _league_name_by_code(league_code)

    await callback.answer(f"Подписка на {league_name} будет подключена на следующем этапе.")
    if callback.message is not None:
        await callback.message.answer(NO_DATA_MESSAGE)


async def handle_table_selected(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(NO_DATA_MESSAGE)


async def handle_current_round_selected(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(NO_DATA_MESSAGE)


async def handle_group_message(message: Message) -> None:
    await message.answer(render_group_not_supported_message())


def create_start_router() -> Router:
    router = Router(name="start")
    router.message(CommandStart(), F.chat.type == "private")(handle_private_start)
    router.message(Command("help"), F.chat.type == "private")(handle_private_help)
    router.message(F.text == MENU_HELP, F.chat.type == "private")(handle_private_help)
    router.message(F.text == MENU_MY_SUBSCRIPTIONS, F.chat.type == "private")(handle_my_subscriptions)
    router.message(F.text == MENU_SUBSCRIBE, F.chat.type == "private")(handle_subscribe_menu)
    router.message(F.text == MENU_STANDINGS, F.chat.type == "private")(handle_standings_menu)
    router.message(F.text == MENU_CURRENT_ROUND, F.chat.type == "private")(handle_current_round_menu)
    router.callback_query(F.data.startswith(CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX))(handle_subscription_toggle)
    router.callback_query(F.data.startswith(CALLBACK_TABLE_PREFIX))(handle_table_selected)
    router.callback_query(F.data.startswith(CALLBACK_CURRENT_ROUND_PREFIX))(handle_current_round_selected)
    router.message(F.chat.type.in_({"group", "supergroup"}))(handle_group_message)
    return router


def _is_admin(message: Message, admin_user_ids: frozenset[int] | None) -> bool:
    if not admin_user_ids or message.from_user is None:
        return False
    return message.from_user.id in admin_user_ids


def _strip_callback_prefix(value: str | None, prefix: str) -> str:
    if value is None or not value.startswith(prefix):
        return ""
    return value.removeprefix(prefix)


def _league_name_by_code(code: str) -> str:
    for league in MVP_LEAGUES:
        if league.code == code:
            return league.name
    return code


router = create_start_router()
