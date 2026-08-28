from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    CALLBACK_ADMIN_LAST_ERROR,
    CALLBACK_ADMIN_NOTIFICATIONS,
    CALLBACK_ADMIN_STATUS,
    CALLBACK_ADMIN_SUBSCRIBERS,
    CALLBACK_ADMIN_SYNC_MENU,
    CALLBACK_ADMIN_SYNC_PREFIX,
    CALLBACK_ADMIN_TEAMS_MENU,
    CALLBACK_ADMIN_TEAMS_PREFIX,
    CALLBACK_ADMIN_TEST_PUSH,
    CALLBACK_ADMIN_TOGGLE_MENU,
    CALLBACK_ADMIN_TOGGLE_PREFIX,
    MENU_ADMIN,
    build_admin_keyboard,
    build_admin_sync_league_keyboard,
    build_admin_teams_league_keyboard,
    build_admin_toggle_league_keyboard,
)
from app.bot.messages import (
    render_admin_menu_message,
    render_admin_subscription_stats,
    render_admin_sync_result,
    render_admin_sync_select_message,
    render_admin_team_list,
    render_admin_teams_select_message,
    render_admin_test_push_message,
    render_admin_toggle_result,
    render_admin_toggle_select_message,
    render_last_parser_error,
    render_parser_status,
    render_recent_notifications,
)
from app.services.admin.service import FootballAdminService


async def handle_admin_menu(message: Message, admin_user_ids: frozenset[int] | None = None) -> None:
    if not _is_admin_message(message, admin_user_ids):
        await message.answer("Админка недоступна.")
        return

    await message.answer(render_admin_menu_message(), reply_markup=build_admin_keyboard())


async def handle_admin_sync_menu(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_admin_sync_select_message(), reply_markup=build_admin_sync_league_keyboard())


async def handle_admin_status(
    callback: CallbackQuery,
    admin_user_ids: frozenset[int] | None = None,
    football_admin_service: FootballAdminService | None = None,
) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        status = await football_admin_service.get_parser_status() if football_admin_service is not None else None
        await callback.message.answer(render_parser_status(status))


async def handle_admin_last_error(
    callback: CallbackQuery,
    admin_user_ids: frozenset[int] | None = None,
    football_admin_service: FootballAdminService | None = None,
) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        error = await football_admin_service.get_last_parser_error() if football_admin_service is not None else None
        await callback.message.answer(render_last_parser_error(error))


async def handle_admin_toggle_menu(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_admin_toggle_select_message(), reply_markup=build_admin_toggle_league_keyboard())


async def handle_admin_subscribers(
    callback: CallbackQuery,
    admin_user_ids: frozenset[int] | None = None,
    football_admin_service: FootballAdminService | None = None,
) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        stats = await football_admin_service.get_subscription_stats() if football_admin_service is not None else None
        await callback.message.answer(render_admin_subscription_stats(stats))


async def handle_admin_notifications(
    callback: CallbackQuery,
    admin_user_ids: frozenset[int] | None = None,
    football_admin_service: FootballAdminService | None = None,
) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        notifications = (
            await football_admin_service.get_recent_notifications(limit=10)
            if football_admin_service is not None
            else ()
        )
        await callback.message.answer(render_recent_notifications(notifications))


async def handle_admin_teams_menu(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_admin_teams_select_message(), reply_markup=build_admin_teams_league_keyboard())


async def handle_admin_teams_league(
    callback: CallbackQuery,
    admin_user_ids: frozenset[int] | None = None,
    football_admin_service: FootballAdminService | None = None,
) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    league_code = _strip_callback_prefix(callback.data, CALLBACK_ADMIN_TEAMS_PREFIX)
    await callback.answer()
    if callback.message is not None:
        if football_admin_service is None or not league_code:
            await callback.message.answer("Данных пока нет.")
            return
        team_list = await football_admin_service.get_league_teams(league_code)
        await callback.message.answer(render_admin_team_list(team_list))


async def handle_admin_test_push(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_admin_test_push_message())


async def handle_admin_sync_league(
    callback: CallbackQuery,
    admin_user_ids: frozenset[int] | None = None,
    football_admin_service: FootballAdminService | None = None,
) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    league_code = _strip_callback_prefix(callback.data, CALLBACK_ADMIN_SYNC_PREFIX)
    await callback.answer()
    if callback.message is not None:
        if football_admin_service is None or not league_code:
            await callback.message.answer("Данных пока нет.")
            return
        await callback.message.answer("Запускаю обновление лиги.")
        result = await football_admin_service.sync_league(league_code)
        await callback.message.answer(render_admin_sync_result(result))


async def handle_admin_toggle_league(
    callback: CallbackQuery,
    admin_user_ids: frozenset[int] | None = None,
    football_admin_service: FootballAdminService | None = None,
) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    league_code = _strip_callback_prefix(callback.data, CALLBACK_ADMIN_TOGGLE_PREFIX)
    await callback.answer()
    if callback.message is not None:
        if football_admin_service is None or not league_code:
            await callback.message.answer("Данных пока нет.")
            return
        try:
            result = await football_admin_service.toggle_league_active(league_code)
        except ValueError:
            await callback.message.answer("Данных пока нет.")
            return
        await callback.message.answer(render_admin_toggle_result(result))


def _is_admin_message(message: Message, admin_user_ids: frozenset[int] | None) -> bool:
    if not admin_user_ids or message.from_user is None:
        return False
    return message.from_user.id in admin_user_ids


async def _ensure_admin_callback(callback: CallbackQuery, admin_user_ids: frozenset[int] | None) -> bool:
    if admin_user_ids and callback.from_user.id in admin_user_ids:
        return True

    await callback.answer("Админка недоступна.", show_alert=True)
    return False


def _strip_callback_prefix(value: str | None, prefix: str) -> str:
    if value is None or not value.startswith(prefix):
        return ""
    return value.removeprefix(prefix)


def create_admin_router() -> Router:
    router = Router(name="admin")
    router.message(F.text == MENU_ADMIN, F.chat.type == "private")(handle_admin_menu)
    router.callback_query(F.data == CALLBACK_ADMIN_SYNC_MENU)(handle_admin_sync_menu)
    router.callback_query(F.data == CALLBACK_ADMIN_STATUS)(handle_admin_status)
    router.callback_query(F.data == CALLBACK_ADMIN_LAST_ERROR)(handle_admin_last_error)
    router.callback_query(F.data == CALLBACK_ADMIN_TOGGLE_MENU)(handle_admin_toggle_menu)
    router.callback_query(F.data == CALLBACK_ADMIN_SUBSCRIBERS)(handle_admin_subscribers)
    router.callback_query(F.data == CALLBACK_ADMIN_NOTIFICATIONS)(handle_admin_notifications)
    router.callback_query(F.data == CALLBACK_ADMIN_TEAMS_MENU)(handle_admin_teams_menu)
    router.callback_query(F.data == CALLBACK_ADMIN_TEST_PUSH)(handle_admin_test_push)
    router.callback_query(F.data.startswith(CALLBACK_ADMIN_SYNC_PREFIX))(handle_admin_sync_league)
    router.callback_query(F.data.startswith(CALLBACK_ADMIN_TOGGLE_PREFIX))(handle_admin_toggle_league)
    router.callback_query(F.data.startswith(CALLBACK_ADMIN_TEAMS_PREFIX))(handle_admin_teams_league)
    return router


router = create_admin_router()
