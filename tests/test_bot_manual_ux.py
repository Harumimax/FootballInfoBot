from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace

from app.bot.dispatcher import create_dispatcher
from app.bot.handlers.start import (
    handle_current_round_selected,
    handle_my_subscriptions,
    handle_private_start,
    handle_subscribe_menu,
    handle_subscription_league_menu,
    handle_subscription_toggle,
    handle_table_selected,
    handle_team_subscription_league_menu,
    handle_team_subscription_league_selected,
    handle_team_subscription_toggle,
)
from app.bot.keyboards import (
    CALLBACK_CURRENT_ROUND_PREFIX,
    CALLBACK_SUBSCRIPTION_LEAGUE_MENU,
    CALLBACK_SUBSCRIPTION_TEAM_LEAGUE_MENU,
    CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX,
    CALLBACK_TEAM_SUBSCRIPTION_LEAGUE_PREFIX,
    CALLBACK_TEAM_SUBSCRIPTION_TOGGLE_PREFIX,
    CALLBACK_TABLE_PREFIX,
    MENU_CURRENT_ROUND,
    MENU_HELP,
    MENU_MY_SUBSCRIPTIONS,
    MENU_STANDINGS,
    MENU_SUBSCRIBE,
    build_active_subscriptions_keyboard,
    build_current_round_league_keyboard,
    build_main_menu_keyboard,
    build_subscription_keyboard,
    build_subscription_type_keyboard,
    build_table_league_keyboard,
    build_team_subscription_keyboard,
)
from app.bot.messages import (
    NO_DATA_MESSAGE,
    render_group_not_supported_message,
    render_help_message,
    render_round_state,
    render_rounds_state,
    render_start_message,
    render_standings,
    render_subscriptions_message,
    render_unsubscribed_message,
)
from app.parser.dto import ParsedMatch, ParsedRound, ParsedStandingRow
from app.services.subscriptions.dto import (
    CurrentRoundView,
    LeagueView,
    StandingTableView,
    SubscriptionToggleResult,
    TeamSubscriptionToggleResult,
    TeamSubscriptionView,
    TeamView,
)


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

    def test_subscription_type_keyboard_offers_league_or_team_path(self) -> None:
        keyboard = build_subscription_type_keyboard()

        self.assertEqual(keyboard.inline_keyboard[0][0].text, "Подписаться на Лигу или Турнир")
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, CALLBACK_SUBSCRIPTION_LEAGUE_MENU)
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "Подписаться на команду")
        self.assertEqual(keyboard.inline_keyboard[1][0].callback_data, CALLBACK_SUBSCRIPTION_TEAM_LEAGUE_MENU)

    def test_active_subscriptions_keyboard_allows_unsubscribe_by_click(self) -> None:
        keyboard = build_active_subscriptions_keyboard(
            leagues=(LeagueView(code="spain", name="Испания"),),
            team_subscriptions=(
                TeamSubscriptionView(
                    league=LeagueView(code="england", name="Англия"),
                    team=TeamView(id=7, name="Арсенал"),
                ),
            ),
        )

        self.assertEqual(keyboard.inline_keyboard[0][0].text, "✓ Испания")
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX}spain")
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "✓ Арсенал (Англия)")
        self.assertEqual(
            keyboard.inline_keyboard[1][0].callback_data,
            f"{CALLBACK_TEAM_SUBSCRIPTION_TOGGLE_PREFIX}england:7",
        )

    def test_team_subscription_keyboard_sorts_and_marks_active_teams(self) -> None:
        keyboard = build_team_subscription_keyboard(
            league_code="spain",
            teams=(TeamView(id=2, name="Севилья"), TeamView(id=1, name="Алавес")),
            subscribed_team_ids=frozenset({2}),
        )

        self.assertEqual(keyboard.inline_keyboard[0][0].text, "Алавес")
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, f"{CALLBACK_TEAM_SUBSCRIPTION_TOGGLE_PREFIX}spain:1")
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "✓ Севилья")

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

    def test_render_standings_is_compact(self) -> None:
        table = StandingTableView(
            league=LeagueView(code="spain", name="Испания"),
            rows=(
                ParsedStandingRow(
                    position=1,
                    team_name="Реал Мадрид",
                    played=2,
                    wins=2,
                    draws=0,
                    losses=0,
                    goals_for=6,
                    goals_against=2,
                    goal_difference=4,
                    points=6,
                ),
                ParsedStandingRow(position=2, team_name="Барселона", played=2, points=4),
            ),
        )

        self.assertEqual(
            render_standings(table),
            "Испания. Турнирная таблица\n\n"
            "1. Реал Мадрид - 2 игр, 6 очк., В2 Н0 П0, мячи 6-2\n"
            "2. Барселона - 2 игр, 4 очк.",
        )

    def test_subscription_messages_are_compact(self) -> None:
        self.assertEqual(render_subscriptions_message(()), "У вас пока нет подписок.")
        self.assertEqual(
            render_subscriptions_message(
                (LeagueView(code="spain", name="Испания"),),
                (
                    TeamSubscriptionView(
                        league=LeagueView(code="england", name="Англия"),
                        team=TeamView(id=7, name="Арсенал"),
                    ),
                ),
            ),
            "Ваши подписки:\n\nНажмите на подписку, чтобы отписаться.",
        )
        self.assertEqual(render_unsubscribed_message("Англии"), "Вы отписались от Англии.")

    def test_dispatcher_registers_router_with_admin_context(self) -> None:
        dispatcher = create_dispatcher(admin_user_ids=frozenset({123}))

        self.assertEqual(dispatcher.workflow_data["admin_user_ids"], frozenset({123}))
        self.assertGreater(len(dispatcher.sub_routers), 0)


class BotLiveUserActionsTest(unittest.IsolatedAsyncioTestCase):
    async def test_start_registers_user_when_service_is_available(self) -> None:
        service = FakeFootballUserService()
        message = FakeMessage(user_id=123, username="max", full_name="Максим")

        await handle_private_start(message, football_user_service=service)

        self.assertEqual(service.registered_profiles[0].telegram_user_id, 123)
        self.assertEqual(message.answers[0].text, render_start_message())

    async def test_my_subscriptions_reads_active_subscriptions(self) -> None:
        service = FakeFootballUserService(
            subscriptions=(LeagueView(code="england", name="Англия"),),
            team_subscriptions=(
                TeamSubscriptionView(
                    league=LeagueView(code="spain", name="Испания"),
                    team=TeamView(id=10, name="Барселона"),
                ),
            ),
        )
        message = FakeMessage(user_id=123)

        await handle_my_subscriptions(message, football_user_service=service)

        self.assertEqual(
            message.answers[0].text,
            "Ваши подписки:\n\nНажмите на подписку, чтобы отписаться.",
        )
        keyboard = message.answers[0].reply_markup
        self.assertEqual(keyboard.inline_keyboard[0][0].text, "✓ Англия")
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "✓ Барселона (Испания)")

    async def test_subscribe_menu_marks_existing_subscriptions(self) -> None:
        message = FakeMessage(user_id=123)

        await handle_subscribe_menu(message)

        keyboard = message.answers[0].reply_markup
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, CALLBACK_SUBSCRIPTION_LEAGUE_MENU)

    async def test_subscription_league_menu_marks_existing_subscriptions(self) -> None:
        service = FakeFootballUserService(subscription_codes=frozenset({"spain"}))
        callback = FakeCallback(data=CALLBACK_SUBSCRIPTION_LEAGUE_MENU, user_id=123)

        await handle_subscription_league_menu(callback, football_user_service=service)

        keyboard = callback.message.answers[0].reply_markup
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "✓ Испания")

    async def test_team_subscription_flow_shows_leagues_then_teams(self) -> None:
        service = FakeFootballUserService(
            teams=(TeamView(id=2, name="Севилья"), TeamView(id=1, name="Алавес")),
            team_subscription_ids=frozenset({1}),
        )
        callback = FakeCallback(data=CALLBACK_SUBSCRIPTION_TEAM_LEAGUE_MENU, user_id=123)

        await handle_team_subscription_league_menu(callback)

        self.assertEqual(
            callback.message.answers[0].reply_markup.inline_keyboard[0][0].callback_data,
            f"{CALLBACK_TEAM_SUBSCRIPTION_LEAGUE_PREFIX}england",
        )

        league_callback = FakeCallback(data=f"{CALLBACK_TEAM_SUBSCRIPTION_LEAGUE_PREFIX}spain", user_id=123)
        await handle_team_subscription_league_selected(league_callback, football_user_service=service)

        self.assertEqual(service.requested_team_leagues, ["spain"])
        keyboard = league_callback.message.answers[0].reply_markup
        self.assertEqual(keyboard.inline_keyboard[0][0].text, "✓ Алавес")
        self.assertEqual(keyboard.inline_keyboard[1][0].text, "Севилья")

    async def test_team_subscription_toggle_sends_status_message(self) -> None:
        service = FakeFootballUserService(
            team_toggle_result=TeamSubscriptionToggleResult(
                league=LeagueView(code="spain", name="Испания"),
                team=TeamView(id=5, name="Барселона"),
                is_active=True,
            )
        )
        callback = FakeCallback(data=f"{CALLBACK_TEAM_SUBSCRIPTION_TOGGLE_PREFIX}spain:5", user_id=123)

        await handle_team_subscription_toggle(callback, football_user_service=service)

        self.assertEqual(service.toggled_teams, [(123, "spain", 5)])
        self.assertEqual(callback.message.answers[0].text, "Вы подписались на Барселона (Испания).")

    async def test_subscription_toggle_sends_current_round_when_enabled(self) -> None:
        round_ = _sample_round()
        service = FakeFootballUserService(
            toggle_result=SubscriptionToggleResult(
                league=LeagueView(code="spain", name="Испания"),
                is_active=True,
                current_round=round_,
            )
        )
        callback = FakeCallback(data=f"{CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX}spain", user_id=123)

        await handle_subscription_toggle(callback, football_user_service=service)

        self.assertEqual(service.toggled, [(123, "spain")])
        self.assertEqual(callback.answers, [""])
        self.assertEqual(callback.message.answers[0].text, render_round_state("Испания", round_))

    async def test_subscription_toggle_sends_visible_rounds_when_enabled(self) -> None:
        round_ = _sample_round()
        catch_up_round = _catch_up_round()
        service = FakeFootballUserService(
            toggle_result=SubscriptionToggleResult(
                league=LeagueView(code="spain", name="Испания"),
                is_active=True,
                current_round=round_,
                current_rounds=(round_, catch_up_round),
            )
        )
        callback = FakeCallback(data=f"{CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX}spain", user_id=123)

        await handle_subscription_toggle(callback, football_user_service=service)

        self.assertEqual(callback.message.answers[0].text, render_rounds_state("Испания", (round_, catch_up_round)))
        self.assertIn("3-й тур", callback.message.answers[0].text)
        self.assertIn("1-й тур", callback.message.answers[0].text)

    async def test_subscription_toggle_sends_unsubscribed_message_when_disabled(self) -> None:
        service = FakeFootballUserService(
            toggle_result=SubscriptionToggleResult(
                league=LeagueView(code="england", name="Англия"),
                is_active=False,
                current_round=None,
            )
        )
        callback = FakeCallback(data=f"{CALLBACK_SUBSCRIPTION_TOGGLE_PREFIX}england", user_id=123)

        await handle_subscription_toggle(callback, football_user_service=service)

        self.assertEqual(callback.message.answers[0].text, "Вы отписались от Англии.")

    async def test_table_selected_reads_latest_standings(self) -> None:
        table = StandingTableView(
            league=LeagueView(code="spain", name="Испания"),
            rows=(ParsedStandingRow(position=1, team_name="Реал Мадрид", played=2, points=6),),
        )
        service = FakeFootballUserService(standings=table)
        callback = FakeCallback(data=f"{CALLBACK_TABLE_PREFIX}spain", user_id=123)

        await handle_table_selected(callback, football_user_service=service)

        self.assertEqual(service.requested_standings, ["spain"])
        self.assertEqual(callback.message.answers[0].text, render_standings(table))

    async def test_current_round_selected_reads_current_round(self) -> None:
        round_view = CurrentRoundView(league=LeagueView(code="spain", name="Испания"), round=_sample_round())
        service = FakeFootballUserService(current_round=round_view)
        callback = FakeCallback(data=f"{CALLBACK_CURRENT_ROUND_PREFIX}spain", user_id=123)

        await handle_current_round_selected(callback, football_user_service=service)

        self.assertEqual(service.requested_rounds, ["spain"])
        self.assertEqual(callback.message.answers[0].text, render_round_state("Испания", round_view.round))

    async def test_current_round_selected_sends_visible_rounds_with_round_labels(self) -> None:
        round_ = _sample_round()
        catch_up_round = _catch_up_round()
        round_view = CurrentRoundView(
            league=LeagueView(code="spain", name="Испания"),
            round=round_,
            rounds=(round_, catch_up_round),
        )
        service = FakeFootballUserService(current_round=round_view)
        callback = FakeCallback(data=f"{CALLBACK_CURRENT_ROUND_PREFIX}spain", user_id=123)

        await handle_current_round_selected(callback, football_user_service=service)

        self.assertEqual(callback.message.answers[0].text, render_rounds_state("Испания", (round_, catch_up_round)))
        self.assertIn("3-й тур", callback.message.answers[0].text)
        self.assertIn("1-й тур", callback.message.answers[0].text)


class FakeAnswer:
    def __init__(self, text: str, reply_markup: object | None) -> None:
        self.text = text
        self.reply_markup = reply_markup


class FakeMessage:
    def __init__(
        self,
        *,
        user_id: int,
        username: str | None = None,
        full_name: str = "Test User",
        language_code: str | None = "ru",
    ) -> None:
        self.from_user = SimpleNamespace(
            id=user_id,
            username=username,
            full_name=full_name,
            language_code=language_code,
        )
        self.answers: list[FakeAnswer] = []

    async def answer(self, text: str, reply_markup: object | None = None) -> None:
        self.answers.append(FakeAnswer(text=text, reply_markup=reply_markup))


class FakeCallback:
    def __init__(self, *, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = FakeMessage(user_id=user_id)
        self.answers: list[str] = []

    async def answer(self, text: str = "") -> None:
        self.answers.append(text)


class FakeFootballUserService:
    def __init__(
        self,
        *,
        subscriptions: tuple[LeagueView, ...] = (),
        subscription_codes: frozenset[str] = frozenset(),
        team_subscriptions: tuple[TeamSubscriptionView, ...] = (),
        team_subscription_ids: frozenset[int] = frozenset(),
        teams: tuple[TeamView, ...] = (),
        toggle_result: SubscriptionToggleResult | None = None,
        team_toggle_result: TeamSubscriptionToggleResult | None = None,
        standings: StandingTableView | None = None,
        current_round: CurrentRoundView | None = None,
    ) -> None:
        self.subscriptions = subscriptions
        self.subscription_codes = subscription_codes
        self.team_subscriptions = team_subscriptions
        self.team_subscription_ids = team_subscription_ids
        self.teams = teams
        self.toggle_result = toggle_result
        self.team_toggle_result = team_toggle_result
        self.standings = standings
        self.current_round = current_round
        self.registered_profiles = []
        self.toggled: list[tuple[int, str]] = []
        self.toggled_teams: list[tuple[int, str, int]] = []
        self.requested_standings: list[str] = []
        self.requested_rounds: list[str] = []
        self.requested_team_leagues: list[str] = []

    async def register_user(self, profile) -> None:
        self.registered_profiles.append(profile)

    async def get_subscriptions(self, telegram_user_id: int) -> tuple[LeagueView, ...]:
        return self.subscriptions

    async def get_team_subscriptions(self, telegram_user_id: int) -> tuple[TeamSubscriptionView, ...]:
        return self.team_subscriptions

    async def get_subscription_codes(self, telegram_user_id: int) -> frozenset[str]:
        return self.subscription_codes

    async def get_team_subscription_ids(self, telegram_user_id: int, league_code: str) -> frozenset[int]:
        return self.team_subscription_ids

    async def get_league_teams(self, league_code: str) -> tuple[TeamView, ...]:
        self.requested_team_leagues.append(league_code)
        return self.teams

    async def toggle_subscription(self, *, telegram_user_id: int, league_code: str) -> SubscriptionToggleResult:
        self.toggled.append((telegram_user_id, league_code))
        assert self.toggle_result is not None
        return self.toggle_result

    async def toggle_team_subscription(
        self,
        *,
        telegram_user_id: int,
        league_code: str,
        team_id: int,
    ) -> TeamSubscriptionToggleResult:
        self.toggled_teams.append((telegram_user_id, league_code, team_id))
        assert self.team_toggle_result is not None
        return self.team_toggle_result

    async def get_latest_standings(self, league_code: str) -> StandingTableView | None:
        self.requested_standings.append(league_code)
        return self.standings

    async def get_current_round(self, league_code: str) -> CurrentRoundView | None:
        self.requested_rounds.append(league_code)
        return self.current_round


def _sample_round() -> ParsedRound:
    return ParsedRound(
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
        ),
    )


def _catch_up_round() -> ParsedRound:
    return ParsedRound(
        number=1,
        source_url="https://football.kulichki.net/spain/2027/1/",
        matches=(
            ParsedMatch(
                home_team="Барселона",
                away_team="Атлетик",
                scheduled_at=datetime(2026, 8, 27, 22, 0),
                home_score=None,
                away_score=None,
                status="scheduled",
            ),
        ),
    )


if __name__ == "__main__":
    unittest.main()
