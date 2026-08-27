from __future__ import annotations

import unittest
from datetime import datetime

from app.bot.dispatcher import create_dispatcher
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
    NO_DATA_MESSAGE,
    render_group_not_supported_message,
    render_help_message,
    render_round_state,
    render_start_message,
    render_subscriptions_message,
    render_unsubscribed_message,
)
from app.parser.dto import ParsedMatch, ParsedRound


class BotManualUxTest(unittest.TestCase):
    def test_start_message_matches_mvp_scope(self) -> None:
        message = render_start_message()

        self.assertIn("FootballInfoBot", message)
        self.assertIn("Англию", message)
        self.assertIn("Испанию", message)

    def test_help_message_contains_source_and_disclaimer(self) -> None:
        message = render_help_message()

        self.assertIn("Источник данных: football.kulichki.net.", message)
        self.assertIn("не является официальным сервисом", message)
        self.assertIn("09:00", message)

    def test_group_message_mentions_later_group_support(self) -> None:
        message = render_group_not_supported_message()

        self.assertIn("личный чат", message)
        self.assertIn("позже", message)

    def test_main_menu_contains_approved_buttons(self) -> None:
        keyboard = build_main_menu_keyboard()
        button_texts = [button.text for row in keyboard.keyboard for button in row]

        self.assertEqual(
            button_texts,
            [
                MENU_MY_SUBSCRIPTIONS,
                MENU_SUBSCRIBE,
                MENU_STANDINGS,
                MENU_CURRENT_ROUND,
                MENU_HELP,
            ],
        )

    def test_subscription_keyboard_marks_active_leagues(self) -> None:
        keyboard = build_subscription_keyboard(subscribed_league_codes=frozenset({"england"}))
        first_button = keyboard.inline_keyboard[0][0]
        second_button = keyboard.inline_keyboard[1][0]

        self.assertEqual(first_button.text, "✓ Англия")
        self.assertEqual(first_button.callback_data, f"{CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX}england")
        self.assertEqual(second_button.text, "Испания")

    def test_manual_league_keyboards_use_all_mvp_leagues(self) -> None:
        table_keyboard = build_table_league_keyboard()
        round_keyboard = build_current_round_league_keyboard()

        self.assertEqual(table_keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_TABLE_PREFIX}england")
        self.assertEqual(table_keyboard.inline_keyboard[1][0].callback_data, f"{CALLBACK_TABLE_PREFIX}spain")
        self.assertEqual(round_keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_CURRENT_ROUND_PREFIX}england")
        self.assertEqual(round_keyboard.inline_keyboard[1][0].callback_data, f"{CALLBACK_CURRENT_ROUND_PREFIX}spain")

    def test_render_round_state_includes_date_time_and_scores(self) -> None:
        round_ = ParsedRound(
            number=3,
            source_url="https://football.kulichki.net/spain/2027/3/",
            matches=(
                ParsedMatch(
                    home_team="Реал",
                    away_team="Барселона",
                    scheduled_at=datetime(2026, 8, 21, 20, 0),
                    home_score=None,
                    away_score=None,
                    status="scheduled",
                ),
                ParsedMatch(
                    home_team="Атлетико",
                    away_team="Вильярреал",
                    scheduled_at=datetime(2026, 8, 22, 21, 0),
                    home_score=2,
                    away_score=1,
                    status="finished",
                ),
            ),
        )

        self.assertEqual(
            render_round_state("Испания", round_),
            "Испания, 3-й тур\n\n"
            "21.08 20:00 Реал - Барселона\n"
            "22.08 21:00 Атлетико 2:1 Вильярреал",
        )

    def test_render_round_state_handles_missing_data(self) -> None:
        self.assertEqual(render_round_state("Испания", None), NO_DATA_MESSAGE)

    def test_subscription_messages_are_compact(self) -> None:
        self.assertEqual(render_subscriptions_message(()), "У вас пока нет подписок.")
        self.assertEqual(render_unsubscribed_message("Англии"), "Вы отписались от Англии.")

    def test_dispatcher_registers_router_with_admin_context(self) -> None:
        dispatcher = create_dispatcher(admin_user_ids=frozenset({123}))

        self.assertEqual(dispatcher.workflow_data["admin_user_ids"], frozenset({123}))
        self.assertGreater(len(dispatcher.sub_routers), 0)


if __name__ == "__main__":
    unittest.main()
