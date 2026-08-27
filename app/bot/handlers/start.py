from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.user_profile import telegram_profile_from_message
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
    render_round_state,
    render_select_league_for_round_message,
    render_select_league_for_table_message,
    render_select_subscription_message,
    render_start_message,
    render_standings,
    render_subscriptions_message,
    render_unsubscribed_message,
)
from app.services.subscriptions.user_service import FootballUserService


async def handle_private_start(
    message: Message,
    admin_user_ids: frozenset[int] | None = None,
    football_user_service: FootballUserService | None = None,
) -> None:
    if football_user_service is not None:
        await football_user_service.register_user(telegram_profile_from_message(message))

    await message.answer(
        render_start_message(),
        reply_markup=build_main_menu_keyboard(is_admin=_is_admin(message, admin_user_ids)),
    )


async def handle_private_help(message: Message) -> None:
    await message.answer(render_help_message())


async def handle_my_subscriptions(message: Message, football_user_service: FootballUserService | None = None) -> None:
    telegram_user_id = _telegram_user_id(message)
    if football_user_service is None or telegram_user_id is None:
        await message.answer(render_empty_subscriptions_message(), reply_markup=build_subscription_keyboard())
        return

    subscriptions = await football_user_service.get_subscriptions(telegram_user_id)
    if subscriptions:
        await message.answer(render_subscriptions_message(subscriptions))
        return

    await message.answer(render_empty_subscriptions_message(), reply_markup=build_subscription_keyboard())


async def handle_subscribe_menu(message: Message, football_user_service: FootballUserService | None = None) -> None:
    telegram_user_id = _telegram_user_id(message)
    subscribed_codes = frozenset()
    if football_user_service is not None and telegram_user_id is not None:
        subscribed_codes = await football_user_service.get_subscription_codes(telegram_user_id)

    await message.answer(
        render_select_subscription_message(),
        reply_markup=build_subscription_keyboard(subscribed_league_codes=subscribed_codes),
    )


async def handle_standings_menu(message: Message) -> None:
    await message.answer(render_select_league_for_table_message(), reply_markup=build_table_league_keyboard())


async def handle_current_round_menu(message: Message) -> None:
    await message.answer(render_select_league_for_round_message(), reply_markup=build_current_round_league_keyboard())


async def handle_subscription_toggle(
    callback: CallbackQuery,
    football_user_service: FootballUserService | None = None,
) -> None:
    league_code = _strip_callback_prefix(callback.data, CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX)
    telegram_user_id = _callback_user_id(callback)

    if football_user_service is None or telegram_user_id is None or not league_code:
        await callback.answer()
        if callback.message is not None:
            await callback.message.answer(NO_DATA_MESSAGE)
        return

    try:
        result = await football_user_service.toggle_subscription(
            telegram_user_id=telegram_user_id,
            league_code=league_code,
        )
    except ValueError:
        await callback.answer()
        if callback.message is not None:
            await callback.message.answer(NO_DATA_MESSAGE)
        return

    await callback.answer()
    if callback.message is not None:
        if result.is_active:
            await callback.message.answer(render_round_state(result.league.name, result.current_round))
        else:
            await callback.message.answer(render_unsubscribed_message(_league_name_for_unsubscribe(result.league.code, result.league.name)))


async def handle_table_selected(callback: CallbackQuery, football_user_service: FootballUserService | None = None) -> None:
    await callback.answer()
    league_code = _strip_callback_prefix(callback.data, CALLBACK_TABLE_PREFIX)
    table = None
    if football_user_service is not None and league_code:
        table = await football_user_service.get_latest_standings(league_code)

    if callback.message is not None:
        await callback.message.answer(render_standings(table))


async def handle_current_round_selected(
    callback: CallbackQuery,
    football_user_service: FootballUserService | None = None,
) -> None:
    await callback.answer()
    league_code = _strip_callback_prefix(callback.data, CALLBACK_CURRENT_ROUND_PREFIX)
    round_view = None
    if football_user_service is not None and league_code:
        round_view = await football_user_service.get_current_round(league_code)

    if callback.message is not None:
        if round_view is None:
            await callback.message.answer(NO_DATA_MESSAGE)
        else:
            await callback.message.answer(render_round_state(round_view.league.name, round_view.round))


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


def _league_name_for_unsubscribe(code: str, default_name: str) -> str:
    names = {
        "england": "Англии",
        "spain": "Испании",
    }
    return names.get(code, default_name)


def _telegram_user_id(message: Message) -> int | None:
    if message.from_user is None:
        return None
    return message.from_user.id


def _callback_user_id(callback: CallbackQuery) -> int | None:
    if callback.from_user is None:
        return None
    return callback.from_user.id


router = create_start_router()
