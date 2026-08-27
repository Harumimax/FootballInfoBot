from __future__ import annotations

import unittest
from datetime import datetime

from app.bot.messages import LeagueView
from app.parser.dto import ParsedMatch, ParsedRound
from app.scheduler.jobs import mvp_push_job_specs
from app.services.notifications import (
    LeagueRoundState,
    PushKind,
    PushNotification,
    PushNotificationService,
    SubscriberView,
    after_matchday_target_date,
    should_run_after_matchday_check,
)


class FakePushRepository:
    def __init__(
        self,
        states: tuple[LeagueRoundState, ...],
        subscribers_by_league: dict[str, tuple[SubscriberView, ...]],
        already_sent_keys: set[str] | None = None,
    ) -> None:
        self.states = states
        self.subscribers_by_league = subscribers_by_league
        self.sent_keys = already_sent_keys or set()
        self.recorded_notifications: list[PushNotification] = []

    async def get_active_league_round_states(self, match_date) -> tuple[LeagueRoundState, ...]:  # noqa: ANN001
        return self.states

    async def get_active_subscribers_for_league(self, league_code: str) -> tuple[SubscriberView, ...]:
        return self.subscribers_by_league.get(league_code, ())

    async def was_notification_sent(self, dedupe_key: str) -> bool:
        return dedupe_key in self.sent_keys

    async def record_notification_sent(self, notification: PushNotification) -> None:
        self.sent_keys.add(notification.dedupe_key)
        self.recorded_notifications.append(notification)


class FakePushSender:
    def __init__(self) -> None:
        self.sent_notifications: list[PushNotification] = []

    async def send(self, notification: PushNotification) -> None:
        self.sent_notifications.append(notification)


class PushNotificationServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_morning_push_sends_full_round_when_league_has_match_today(self) -> None:
        repository = FakePushRepository(
            states=(
                LeagueRoundState(
                    league=LeagueView(code="spain", name="Испания"),
                    round=_sample_round(),
                    has_match_today=True,
                    all_today_matches_finished=False,
                    has_changes_today=False,
                ),
            ),
            subscribers_by_league={"spain": (SubscriberView(user_id=1, telegram_user_id=1001),)},
        )
        sender = FakePushSender()
        service = PushNotificationService(repository=repository, sender=sender)

        result = await service.send_morning_pushes(datetime(2026, 8, 27, 9, 0))

        self.assertEqual(result.kind, PushKind.MORNING)
        self.assertEqual(result.sent_count, 1)
        self.assertEqual(result.skipped_leagues, ())
        self.assertEqual(len(sender.sent_notifications), 1)
        self.assertEqual(sender.sent_notifications[0].telegram_user_id, 1001)
        self.assertEqual(sender.sent_notifications[0].dedupe_key, "morning:2026-08-27:spain:1001")
        self.assertIn("21.08 20:00 Реал - Барселона", sender.sent_notifications[0].text)
        self.assertIn("22.08 21:00 Атлетико 2:1 Вильярреал", sender.sent_notifications[0].text)

    async def test_morning_push_skips_league_without_matches_today(self) -> None:
        repository = FakePushRepository(
            states=(
                LeagueRoundState(
                    league=LeagueView(code="england", name="Англия"),
                    round=_sample_round(),
                    has_match_today=False,
                    all_today_matches_finished=False,
                    has_changes_today=False,
                ),
            ),
            subscribers_by_league={"england": (SubscriberView(user_id=1, telegram_user_id=1001),)},
        )
        sender = FakePushSender()
        service = PushNotificationService(repository=repository, sender=sender)

        result = await service.send_morning_pushes(datetime(2026, 8, 27, 9, 0))

        self.assertEqual(result.sent_count, 0)
        self.assertEqual(result.skipped_leagues, ("england",))
        self.assertEqual(sender.sent_notifications, [])

    async def test_push_dedupe_prevents_duplicate_send(self) -> None:
        notification_key = "morning:2026-08-27:spain:1001"
        repository = FakePushRepository(
            states=(
                LeagueRoundState(
                    league=LeagueView(code="spain", name="Испания"),
                    round=_sample_round(),
                    has_match_today=True,
                    all_today_matches_finished=False,
                    has_changes_today=False,
                ),
            ),
            subscribers_by_league={"spain": (SubscriberView(user_id=1, telegram_user_id=1001),)},
            already_sent_keys={notification_key},
        )
        sender = FakePushSender()
        service = PushNotificationService(repository=repository, sender=sender)

        result = await service.send_morning_pushes(datetime(2026, 8, 27, 9, 0))

        self.assertEqual(result.sent_count, 0)
        self.assertEqual(sender.sent_notifications, [])

    async def test_after_matchday_push_waits_when_matches_are_not_finished_before_last_check(self) -> None:
        repository = FakePushRepository(
            states=(
                LeagueRoundState(
                    league=LeagueView(code="spain", name="Испания"),
                    round=_sample_round(),
                    has_match_today=True,
                    all_today_matches_finished=False,
                    has_changes_today=True,
                ),
            ),
            subscribers_by_league={"spain": (SubscriberView(user_id=1, telegram_user_id=1001),)},
        )
        sender = FakePushSender()
        service = PushNotificationService(repository=repository, sender=sender)

        result = await service.check_after_matchday_pushes(datetime(2026, 8, 27, 23, 0))

        self.assertEqual(result.sent_count, 0)
        self.assertEqual(result.pending_leagues, ("spain",))
        self.assertEqual(sender.sent_notifications, [])

    async def test_after_matchday_push_sends_when_all_today_matches_are_finished(self) -> None:
        repository = FakePushRepository(
            states=(
                LeagueRoundState(
                    league=LeagueView(code="spain", name="Испания"),
                    round=_sample_round(),
                    has_match_today=True,
                    all_today_matches_finished=True,
                    has_changes_today=True,
                ),
            ),
            subscribers_by_league={"spain": (SubscriberView(user_id=1, telegram_user_id=1001),)},
        )
        sender = FakePushSender()
        service = PushNotificationService(repository=repository, sender=sender)

        result = await service.check_after_matchday_pushes(datetime(2026, 8, 28, 0, 0))

        self.assertEqual(result.sent_count, 1)
        self.assertEqual(result.pending_leagues, ())
        self.assertEqual(sender.sent_notifications[0].kind, PushKind.AFTER_MATCHDAY)
        self.assertEqual(sender.sent_notifications[0].dedupe_key, "after_matchday:2026-08-27:spain:1001")

    async def test_after_matchday_push_sends_as_is_at_03_when_there_are_changes(self) -> None:
        repository = FakePushRepository(
            states=(
                LeagueRoundState(
                    league=LeagueView(code="england", name="Англия"),
                    round=_sample_round(),
                    has_match_today=True,
                    all_today_matches_finished=False,
                    has_changes_today=True,
                ),
            ),
            subscribers_by_league={"england": (SubscriberView(user_id=1, telegram_user_id=1001),)},
        )
        sender = FakePushSender()
        service = PushNotificationService(repository=repository, sender=sender)

        result = await service.check_after_matchday_pushes(datetime(2026, 8, 28, 3, 0))

        self.assertEqual(result.sent_count, 1)
        self.assertEqual(result.pending_leagues, ())
        self.assertEqual(sender.sent_notifications[0].dedupe_key, "after_matchday:2026-08-27:england:1001")

    async def test_after_matchday_push_does_not_send_at_03_without_changes(self) -> None:
        repository = FakePushRepository(
            states=(
                LeagueRoundState(
                    league=LeagueView(code="england", name="Англия"),
                    round=_sample_round(),
                    has_match_today=True,
                    all_today_matches_finished=False,
                    has_changes_today=False,
                ),
            ),
            subscribers_by_league={"england": (SubscriberView(user_id=1, telegram_user_id=1001),)},
        )
        sender = FakePushSender()
        service = PushNotificationService(repository=repository, sender=sender)

        result = await service.check_after_matchday_pushes(datetime(2026, 8, 28, 3, 0))

        self.assertEqual(result.sent_count, 0)
        self.assertEqual(result.pending_leagues, ("england",))
        self.assertEqual(sender.sent_notifications, [])

    def test_after_matchday_check_window(self) -> None:
        self.assertTrue(should_run_after_matchday_check(datetime(2026, 8, 27, 23, 0)))
        self.assertTrue(should_run_after_matchday_check(datetime(2026, 8, 28, 0, 0)))
        self.assertTrue(should_run_after_matchday_check(datetime(2026, 8, 28, 3, 0)))
        self.assertFalse(should_run_after_matchday_check(datetime(2026, 8, 28, 4, 0)))
        self.assertFalse(should_run_after_matchday_check(datetime(2026, 8, 27, 22, 0)))

    def test_after_matchday_target_date_uses_previous_date_after_midnight(self) -> None:
        self.assertEqual(after_matchday_target_date(datetime(2026, 8, 27, 23, 0)).isoformat(), "2026-08-27")
        self.assertEqual(after_matchday_target_date(datetime(2026, 8, 28, 0, 0)).isoformat(), "2026-08-27")
        self.assertEqual(after_matchday_target_date(datetime(2026, 8, 28, 3, 0)).isoformat(), "2026-08-27")
        self.assertEqual(after_matchday_target_date(datetime(2026, 8, 28, 4, 0)).isoformat(), "2026-08-28")

    def test_mvp_push_job_specs_document_schedule(self) -> None:
        specs = mvp_push_job_specs()

        self.assertEqual(
            [(spec.name, spec.hour, spec.minute) for spec in specs],
            [
                ("morning_push", 9, 0),
                ("after_matchday_check", 23, 0),
                ("after_matchday_check", 0, 0),
                ("after_matchday_check", 1, 0),
                ("after_matchday_check", 2, 0),
                ("after_matchday_check", 3, 0),
            ],
        )


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


if __name__ == "__main__":
    unittest.main()
