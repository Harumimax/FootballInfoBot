from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace

from app.bot.dispatcher import create_dispatcher
from app.bot.handlers.admin import (
    handle_admin_last_error,
    handle_admin_notifications,
    handle_admin_status,
    handle_admin_subscribers,
    handle_admin_sync_league,
    handle_admin_teams_league,
    handle_admin_test_push,
    handle_admin_toggle_league,
)
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
    build_main_menu_keyboard,
)
from app.bot.messages import (
    LeagueParserStatusView,
    ParserStatusView,
    league_name_by_code,
    render_admin_menu_message,
    render_admin_subscription_stats,
    render_admin_sync_result,
    render_admin_sync_select_message,
    render_admin_team_list,
    render_admin_test_push_message,
    render_admin_toggle_result,
    render_admin_toggle_select_message,
    render_last_parser_error,
    render_parser_status,
    render_recent_notifications,
)
from app.services.admin.dto import AdminSubscriptionStatsView, AdminSyncResult, AdminTeamListView, LeagueToggleResult, RecentNotificationView
from app.services.subscriptions.dto import LeagueView, TeamView


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
                CALLBACK_ADMIN_SUBSCRIBERS,
                CALLBACK_ADMIN_NOTIFICATIONS,
                CALLBACK_ADMIN_TEAMS_MENU,
                CALLBACK_ADMIN_TEST_PUSH,
            ],
        )

    def test_admin_league_keyboards_use_mvp_leagues(self) -> None:
        sync_keyboard = build_admin_sync_league_keyboard()
        toggle_keyboard = build_admin_toggle_league_keyboard()
        teams_keyboard = build_admin_teams_league_keyboard()

        self.assertEqual(sync_keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_ADMIN_SYNC_PREFIX}england")
        self.assertEqual(sync_keyboard.inline_keyboard[1][0].callback_data, f"{CALLBACK_ADMIN_SYNC_PREFIX}spain")
        self.assertEqual(sync_keyboard.inline_keyboard[2][0].callback_data, f"{CALLBACK_ADMIN_SYNC_PREFIX}germany")
        self.assertEqual(sync_keyboard.inline_keyboard[3][0].callback_data, f"{CALLBACK_ADMIN_SYNC_PREFIX}italy")
        self.assertEqual(sync_keyboard.inline_keyboard[4][0].callback_data, f"{CALLBACK_ADMIN_SYNC_PREFIX}france")
        self.assertEqual(sync_keyboard.inline_keyboard[5][0].callback_data, f"{CALLBACK_ADMIN_SYNC_PREFIX}ruschamp")
        self.assertEqual(toggle_keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_ADMIN_TOGGLE_PREFIX}england")
        self.assertEqual(toggle_keyboard.inline_keyboard[1][0].callback_data, f"{CALLBACK_ADMIN_TOGGLE_PREFIX}spain")
        self.assertEqual(toggle_keyboard.inline_keyboard[2][0].callback_data, f"{CALLBACK_ADMIN_TOGGLE_PREFIX}germany")
        self.assertEqual(toggle_keyboard.inline_keyboard[3][0].callback_data, f"{CALLBACK_ADMIN_TOGGLE_PREFIX}italy")
        self.assertEqual(toggle_keyboard.inline_keyboard[4][0].callback_data, f"{CALLBACK_ADMIN_TOGGLE_PREFIX}france")
        self.assertEqual(toggle_keyboard.inline_keyboard[5][0].callback_data, f"{CALLBACK_ADMIN_TOGGLE_PREFIX}ruschamp")
        self.assertEqual(teams_keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_ADMIN_TEAMS_PREFIX}england")
        self.assertEqual(teams_keyboard.inline_keyboard[1][0].callback_data, f"{CALLBACK_ADMIN_TEAMS_PREFIX}spain")
        self.assertEqual(teams_keyboard.inline_keyboard[2][0].callback_data, f"{CALLBACK_ADMIN_TEAMS_PREFIX}germany")
        self.assertEqual(teams_keyboard.inline_keyboard[3][0].callback_data, f"{CALLBACK_ADMIN_TEAMS_PREFIX}italy")
        self.assertEqual(teams_keyboard.inline_keyboard[4][0].callback_data, f"{CALLBACK_ADMIN_TEAMS_PREFIX}france")
        self.assertEqual(teams_keyboard.inline_keyboard[5][0].callback_data, f"{CALLBACK_ADMIN_TEAMS_PREFIX}ruschamp")

    def test_admin_messages_are_compact_and_actionable(self) -> None:
        self.assertEqual(render_admin_menu_message(), "Админка FootballInfoBot.")
        self.assertEqual(render_admin_sync_select_message(), "Выберите лигу для принудительного обновления.")
        self.assertEqual(render_admin_toggle_select_message(), "Выберите лигу, которую нужно включить или отключить.")
        self.assertIn(
            "Англия: обновление завершено.",
            render_admin_sync_result(
                AdminSyncResult(league_name="Англия", status="success", parsed_matches=10, parsed_standings_rows=20)
            ),
        )
        self.assertEqual(
            render_admin_toggle_result(LeagueToggleResult(league_name="Испания", is_active=False)),
            "Испания: лига отключена.",
        )
        self.assertIn(
            "Подписок на команды: 3",
            render_admin_subscription_stats(
                AdminSubscriptionStatsView(
                    users_count=2,
                    active_league_subscriptions=4,
                    active_team_subscriptions=3,
                )
            ),
        )
        self.assertEqual(render_admin_test_push_message(), "Тестовый пуш FootballInfoBot. Если вы видите это сообщение, отправка в Telegram работает.")

    def test_recent_notifications_and_team_list_messages_are_compact(self) -> None:
        notifications = (
            RecentNotificationView(
                created_at=datetime(2026, 8, 28, 9, 0),
                telegram_user_id=123,
                message_type="digest",
                status="sent",
                dedupe_key="morning:2026-08-28:spain:123",
            ),
        )
        team_list = AdminTeamListView(
            league=LeagueView(code="spain", name="Испания"),
            teams=(TeamView(id=2, name="Барселона"), TeamView(id=1, name="Реал Мадрид")),
        )

        self.assertIn("28.08 09:00 | 123 | digest | sent", render_recent_notifications(notifications))
        self.assertEqual(render_recent_notifications(()), "Уведомлений пока нет.")
        self.assertEqual(render_admin_team_list(team_list), "Испания. Команды:\n\nБарселона\nРеал Мадрид")

    def test_parser_status_defaults_to_mvp_leagues(self) -> None:
        message = render_parser_status()

        self.assertIn("Статус парсера:", message)
        self.assertIn("Англия: последнее успешное обновление нет данных, включена", message)
        self.assertIn("Испания: последнее успешное обновление нет данных, включена", message)
        self.assertIn("Германия: последнее успешное обновление нет данных, включена", message)
        self.assertIn("Италия: последнее успешное обновление нет данных, включена", message)
        self.assertIn("Франция: последнее успешное обновление нет данных, включена", message)
        self.assertIn("Россия: последнее успешное обновление нет данных, включена", message)
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
        self.assertEqual(league_name_by_code("germany"), "Германия")
        self.assertEqual(league_name_by_code("ruschamp"), "Россия")
        self.assertEqual(league_name_by_code("unknown"), "unknown")

    def test_dispatcher_registers_admin_and_start_routers(self) -> None:
        dispatcher = create_dispatcher(admin_user_ids=frozenset({123}))

        router_names = {router.name for router in dispatcher.sub_routers}
        self.assertIn("admin", router_names)
        self.assertIn("start", router_names)


class AdminLiveActionsTest(unittest.IsolatedAsyncioTestCase):
    async def test_status_reads_admin_service(self) -> None:
        service = FakeAdminService(status=_status())
        callback = FakeCallback(data=CALLBACK_ADMIN_STATUS, user_id=123)

        await handle_admin_status(callback, admin_user_ids=frozenset({123}), football_admin_service=service)

        self.assertEqual(callback.answers, [""])
        self.assertEqual(callback.message.answers[0].text, render_parser_status(_status()))

    async def test_last_error_reads_admin_service(self) -> None:
        service = FakeAdminService(last_error="timeout")
        callback = FakeCallback(data=CALLBACK_ADMIN_LAST_ERROR, user_id=123)

        await handle_admin_last_error(callback, admin_user_ids=frozenset({123}), football_admin_service=service)

        self.assertEqual(callback.message.answers[0].text, "Последняя ошибка парсера:\n\ntimeout")

    async def test_sync_league_runs_admin_service(self) -> None:
        result = AdminSyncResult(league_name="Испания", status="success", parsed_matches=14, parsed_standings_rows=20)
        service = FakeAdminService(sync_result=result)
        callback = FakeCallback(data=f"{CALLBACK_ADMIN_SYNC_PREFIX}spain", user_id=123)

        await handle_admin_sync_league(callback, admin_user_ids=frozenset({123}), football_admin_service=service)

        self.assertEqual(service.synced_codes, ["spain"])
        self.assertEqual(callback.message.answers[0].text, "Запускаю обновление лиги.")
        self.assertEqual(callback.message.answers[1].text, render_admin_sync_result(result))

    async def test_toggle_league_runs_admin_service(self) -> None:
        result = LeagueToggleResult(league_name="Англия", is_active=False)
        service = FakeAdminService(toggle_result=result)
        callback = FakeCallback(data=f"{CALLBACK_ADMIN_TOGGLE_PREFIX}england", user_id=123)

        await handle_admin_toggle_league(callback, admin_user_ids=frozenset({123}), football_admin_service=service)

        self.assertEqual(service.toggled_codes, ["england"])
        self.assertEqual(callback.message.answers[0].text, "Англия: лига отключена.")

    async def test_subscribers_reads_admin_service(self) -> None:
        stats = AdminSubscriptionStatsView(users_count=2, active_league_subscriptions=3, active_team_subscriptions=1)
        service = FakeAdminService(subscription_stats=stats)
        callback = FakeCallback(data=CALLBACK_ADMIN_SUBSCRIBERS, user_id=123)

        await handle_admin_subscribers(callback, admin_user_ids=frozenset({123}), football_admin_service=service)

        self.assertEqual(callback.message.answers[0].text, render_admin_subscription_stats(stats))

    async def test_notifications_reads_admin_service(self) -> None:
        notification = RecentNotificationView(
            created_at=datetime(2026, 8, 28, 9, 0),
            telegram_user_id=123,
            message_type="digest",
            status="sent",
            dedupe_key="morning:2026-08-28:spain:123",
        )
        service = FakeAdminService(recent_notifications=(notification,))
        callback = FakeCallback(data=CALLBACK_ADMIN_NOTIFICATIONS, user_id=123)

        await handle_admin_notifications(callback, admin_user_ids=frozenset({123}), football_admin_service=service)

        self.assertEqual(service.requested_notification_limits, [10])
        self.assertEqual(callback.message.answers[0].text, render_recent_notifications((notification,)))

    async def test_teams_league_reads_admin_service(self) -> None:
        team_list = AdminTeamListView(
            league=LeagueView(code="spain", name="Испания"),
            teams=(TeamView(id=1, name="Барселона"),),
        )
        service = FakeAdminService(team_list=team_list)
        callback = FakeCallback(data=f"{CALLBACK_ADMIN_TEAMS_PREFIX}spain", user_id=123)

        await handle_admin_teams_league(callback, admin_user_ids=frozenset({123}), football_admin_service=service)

        self.assertEqual(service.requested_team_codes, ["spain"])
        self.assertEqual(callback.message.answers[0].text, render_admin_team_list(team_list))

    async def test_test_push_sends_message_to_admin_chat(self) -> None:
        callback = FakeCallback(data=CALLBACK_ADMIN_TEST_PUSH, user_id=123)

        await handle_admin_test_push(callback, admin_user_ids=frozenset({123}))

        self.assertEqual(callback.message.answers[0].text, render_admin_test_push_message())

    async def test_regular_user_cannot_run_admin_callback(self) -> None:
        service = FakeAdminService(status=_status())
        callback = FakeCallback(data=CALLBACK_ADMIN_STATUS, user_id=456)

        await handle_admin_status(callback, admin_user_ids=frozenset({123}), football_admin_service=service)

        self.assertEqual(callback.answers, ["Админка недоступна."])
        self.assertEqual(callback.message.answers, [])


class FakeAnswer:
    def __init__(self, text: str, reply_markup: object | None) -> None:
        self.text = text
        self.reply_markup = reply_markup


class FakeMessage:
    def __init__(self, *, user_id: int) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.answers: list[FakeAnswer] = []

    async def answer(self, text: str, reply_markup: object | None = None) -> None:
        self.answers.append(FakeAnswer(text=text, reply_markup=reply_markup))


class FakeCallback:
    def __init__(self, *, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = FakeMessage(user_id=user_id)
        self.answers: list[str] = []

    async def answer(self, text: str = "", show_alert: bool = False) -> None:
        self.answers.append(text)


class FakeAdminService:
    def __init__(
        self,
        *,
        status: ParserStatusView | None = None,
        last_error: str | None = None,
        sync_result: AdminSyncResult | None = None,
        toggle_result: LeagueToggleResult | None = None,
        subscription_stats: AdminSubscriptionStatsView | None = None,
        recent_notifications: tuple[RecentNotificationView, ...] = (),
        team_list: AdminTeamListView | None = None,
    ) -> None:
        self.status = status
        self.last_error = last_error
        self.sync_result = sync_result
        self.toggle_result = toggle_result
        self.subscription_stats = subscription_stats
        self.recent_notifications = recent_notifications
        self.team_list = team_list
        self.synced_codes: list[str] = []
        self.toggled_codes: list[str] = []
        self.requested_notification_limits: list[int] = []
        self.requested_team_codes: list[str] = []

    async def get_parser_status(self) -> ParserStatusView:
        assert self.status is not None
        return self.status

    async def get_last_parser_error(self) -> str | None:
        return self.last_error

    async def sync_league(self, league_code: str) -> AdminSyncResult:
        self.synced_codes.append(league_code)
        assert self.sync_result is not None
        return self.sync_result

    async def toggle_league_active(self, league_code: str) -> LeagueToggleResult:
        self.toggled_codes.append(league_code)
        assert self.toggle_result is not None
        return self.toggle_result

    async def get_subscription_stats(self) -> AdminSubscriptionStatsView:
        assert self.subscription_stats is not None
        return self.subscription_stats

    async def get_recent_notifications(self, limit: int = 10) -> tuple[RecentNotificationView, ...]:
        self.requested_notification_limits.append(limit)
        return self.recent_notifications

    async def get_league_teams(self, league_code: str) -> AdminTeamListView | None:
        self.requested_team_codes.append(league_code)
        return self.team_list


def _status() -> ParserStatusView:
    return ParserStatusView(
        leagues=(
            LeagueParserStatusView(
                league_name="Испания",
                last_success_at=datetime(2026, 8, 28, 9, 0),
                is_active=True,
            ),
        ),
        last_run_at=datetime(2026, 8, 28, 9, 0),
        last_run_status="success",
    )


if __name__ == "__main__":
    unittest.main()
