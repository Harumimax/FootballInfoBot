from __future__ import annotations

import unittest
from datetime import datetime

from app.bot.dispatcher import create_dispatcher
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
    build_main_menu_keyboard,
)
from app.bot.messages import (
    LeagueParserStatusView,
    ParserStatusView,
    league_name_by_code,
    render_admin_menu_message,
    render_admin_sync_placeholder,
    render_admin_sync_select_message,
    render_admin_toggle_placeholder,
    render_admin_toggle_select_message,
    render_last_parser_error,
    render_parser_status,
)


class AdminUxTest(unittest.TestCase):
    def test_main_menu_shows_admin_button_only_for_admins(self) -> None:
        regular_keyboard = build_main_menu_keyboard(is_admin=False)
        admin_keyboard = build_main_menu_keyboard(is_admin=True)

        regular_texts = [button.text for row in regular_keyboard.keyboard for button in row]
        admin_texts = [button.text for row in admin_keyboard.keyboard for button in row]

        self.assertNotIn(MENU_ADMIN, regular_texts)
        self.assertIn(MENU_ADMIN, admin_texts)

    def test_admin_keyboard_contains_mvp_actions(self) -> None:
        keyboard = build_admin_keyboard()
        callback_data = [button.callback_data for row in keyboard.inline_keyboard for button in row]

        self.assertEqual(
            callback_data,
            [
                CALLBACK_ADMIN_SYNC_MENU,
                CALLBACK_ADMIN_STATUS,
                CALLBACK_ADMIN_LAST_ERROR,
                CALLBACK_ADMIN_TOGGLE_MENU,
            ],
        )

    def test_admin_league_keyboards_use_mvp_leagues(self) -> None:
        sync_keyboard = build_admin_sync_league_keyboard()
        toggle_keyboard = build_admin_toggle_league_keyboard()

        self.assertEqual(sync_keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_ADMIN_SYNC_PREFIX}england")
        self.assertEqual(sync_keyboard.inline_keyboard[1][0].callback_data, f"{CALLBACK_ADMIN_SYNC_PREFIX}spain")
        self.assertEqual(toggle_keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_ADMIN_TOGGLE_PREFIX}england")
        self.assertEqual(toggle_keyboard.inline_keyboard[1][0].callback_data, f"{CALLBACK_ADMIN_TOGGLE_PREFIX}spain")

    def test_admin_messages_are_compact_and_actionable(self) -> None:
        self.assertEqual(render_admin_menu_message(), "Админка FootballInfoBot.")
        self.assertEqual(render_admin_sync_select_message(), "Выберите лигу для принудительного обновления.")
        self.assertEqual(render_admin_toggle_select_message(), "Выберите лигу, которую нужно включить или отключить.")
        self.assertIn("Англия", render_admin_sync_placeholder("Англия"))
        self.assertIn("Испания", render_admin_toggle_placeholder("Испания"))

    def test_parser_status_defaults_to_mvp_leagues(self) -> None:
        message = render_parser_status()

        self.assertIn("Статус парсера:", message)
        self.assertIn("Англия: последнее успешное обновление нет данных, включена", message)
        self.assertIn("Испания: последнее успешное обновление нет данных, включена", message)
        self.assertIn("Последний запуск: нет данных", message)

    def test_parser_status_renders_known_values(self) -> None:
        message = render_parser_status(
            ParserStatusView(
                leagues=(
                    LeagueParserStatusView(
                        league_name="Англия",
                        last_success_at=datetime(2026, 8, 27, 9, 2),
                        is_active=True,
                    ),
                    LeagueParserStatusView(
                        league_name="Испания",
                        last_success_at=None,
                        is_active=False,
                    ),
                ),
                last_run_at=datetime(2026, 8, 27, 23, 0),
                last_run_status="failed",
                last_error="HTTP 500",
            )
        )

        self.assertIn("Англия: последнее успешное обновление 27.08 09:02, включена", message)
        self.assertIn("Испания: последнее успешное обновление нет данных, отключена", message)
        self.assertIn("Последний запуск: 27.08 23:00", message)
        self.assertIn("Статус: failed", message)
        self.assertIn("Последняя ошибка: HTTP 500", message)

    def test_last_parser_error_message(self) -> None:
        self.assertEqual(render_last_parser_error(), "Ошибок парсера пока нет.")
        self.assertEqual(render_last_parser_error("timeout"), "Последняя ошибка парсера:\n\ntimeout")

    def test_league_name_by_code_falls_back_to_code(self) -> None:
        self.assertEqual(league_name_by_code("england"), "Англия")
        self.assertEqual(league_name_by_code("unknown"), "unknown")

    def test_dispatcher_registers_admin_and_start_routers(self) -> None:
        dispatcher = create_dispatcher(admin_user_ids=frozenset({123}))

        router_names = {router.name for router in dispatcher.sub_routers}
        self.assertIn("admin", router_names)
        self.assertIn("start", router_names)


if __name__ == "__main__":
    unittest.main()
