from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    CALLBACK_ADMIN_LAST_ERROR,
    CALLBACK_ADMIN_STATUS,
    CALLBACK_ADMIN_SYNC_MENU,
    CALLBACK_ADMIN_SYNC_PREFIX,
    CALLBACK_ADMIN_TOGGLE_MENU,
    CALLBACK_ADMIN_TOGGLE_PREFIX,
    MENU_ADMIN,
    build_admin_keyboard,
    build_admin_sync_league_keyboard,
    build_admin_toggle_league_keyboard,
)
from app.bot.messages import (
    league_name_by_code,
    render_admin_menu_message,
    render_admin_sync_placeholder,
    render_admin_sync_select_message,
    render_admin_toggle_placeholder,
    render_admin_toggle_select_message,
    render_last_parser_error,
    render_parser_status,
)


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


async def handle_admin_status(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_parser_status())


async def handle_admin_last_error(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_last_parser_error())


async def handle_admin_toggle_menu(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_admin_toggle_select_message(), reply_markup=build_admin_toggle_league_keyboard())


async def handle_admin_sync_league(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    league_name = league_name_by_code(_strip_callback_prefix(callback.data, CALLBACK_ADMIN_SYNC_PREFIX))
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_admin_sync_placeholder(league_name))


async def handle_admin_toggle_league(callback: CallbackQuery, admin_user_ids: frozenset[int] | None = None) -> None:
    if not await _ensure_admin_callback(callback, admin_user_ids):
        return

    league_name = league_name_by_code(_strip_callback_prefix(callback.data, CALLBACK_ADMIN_TOGGLE_PREFIX))
    await callback.answer()
    if callback.message is not None:
        await callback.message.answer(render_admin_toggle_placeholder(league_name))


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
    router.callback_query(F.data.startswith(CALLBACK_ADMIN_SYNC_PREFIX))(handle_admin_sync_league)
    router.callback_query(F.data.startswith(CALLBACK_ADMIN_TOGGLE_PREFIX))(handle_admin_toggle_league)
    return router


router = create_admin_router()
