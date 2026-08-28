from __future__ import annotations

from datetime import datetime

from app.bot.messages.rendering import LeagueView, MVP_LEAGUES
from app.services.admin.dto import (
    AdminSubscriptionStatsView,
    AdminSyncResult,
    AdminTeamListView,
    LeagueParserStatusView,
    LeagueToggleResult,
    ParserStatusView,
    RecentNotificationView,
)


NO_PARSER_ERROR_MESSAGE = "Ошибок парсера пока нет."


def render_admin_menu_message() -> str:
    return "Админка FootballInfoBot."


def render_admin_sync_select_message() -> str:
    return "Выберите лигу для принудительного обновления."


def render_admin_toggle_select_message() -> str:
    return "Выберите лигу, которую нужно включить или отключить."


def render_admin_teams_select_message() -> str:
    return "Выберите лигу, чтобы посмотреть команды."


def render_admin_sync_result(result: AdminSyncResult) -> str:
    if result.status == "success":
        return (
            f"{result.league_name}: обновление завершено.\n\n"
            f"Матчей: {result.parsed_matches}\n"
            f"Строк таблицы: {result.parsed_standings_rows}"
        )
    if result.status == "skipped":
        return f"{result.league_name}: обновление пропущено."
    return f"{result.league_name}: ошибка обновления.\n\n{result.error_message or 'Данных пока нет'}"


def render_admin_toggle_result(result: LeagueToggleResult) -> str:
    state = "включена" if result.is_active else "отключена"
    return f"{result.league_name}: лига {state}."


def render_parser_status(status: ParserStatusView | None = None) -> str:
    if status is None:
        status = ParserStatusView(
            leagues=tuple(
                LeagueParserStatusView(league_name=league.name, last_success_at=None, is_active=True)
                for league in MVP_LEAGUES
            )
        )

    lines = ["Статус парсера:", ""]

    for league in status.leagues:
        active_label = "включена" if league.is_active else "отключена"
        last_success = _format_datetime(league.last_success_at)
        lines.append(f"{league.league_name}: последнее успешное обновление {last_success}, {active_label}")

    lines.append("")
    lines.append(f"Последний запуск: {_format_datetime(status.last_run_at)}")
    lines.append(f"Статус: {status.last_run_status or 'нет данных'}")

    if status.last_error:
        lines.append(f"Последняя ошибка: {status.last_error}")

    return "\n".join(lines)


def render_last_parser_error(error_message: str | None = None) -> str:
    if not error_message:
        return NO_PARSER_ERROR_MESSAGE
    return f"Последняя ошибка парсера:\n\n{error_message}"


def render_admin_subscription_stats(stats: AdminSubscriptionStatsView | None = None) -> str:
    if stats is None:
        return "Активные подписки:\n\nДанных пока нет."

    return (
        "Активные подписки:\n\n"
        f"Пользователей: {stats.users_count}\n"
        f"Подписок на лиги: {stats.active_league_subscriptions}\n"
        f"Подписок на команды: {stats.active_team_subscriptions}"
    )


def render_recent_notifications(notifications: tuple[RecentNotificationView, ...]) -> str:
    if not notifications:
        return "Уведомлений пока нет."

    lines = ["Последние уведомления:"]
    for notification in notifications:
        key = notification.dedupe_key or "без ключа"
        error = f", ошибка: {notification.error_message}" if notification.error_message else ""
        lines.append(
            f"{_format_datetime(notification.created_at)} | "
            f"{notification.telegram_user_id} | "
            f"{notification.message_type} | "
            f"{notification.status} | "
            f"{key}{error}"
        )
    return "\n".join(lines)


def render_admin_team_list(team_list: AdminTeamListView | None = None) -> str:
    if team_list is None or not team_list.teams:
        return "Команды лиги:\n\nДанных пока нет."

    lines = [f"{team_list.league.name}. Команды:", ""]
    lines.extend(team.name for team in team_list.teams)
    return "\n".join(lines)


def render_admin_test_push_message() -> str:
    return "Тестовый пуш FootballInfoBot. Если вы видите это сообщение, отправка в Telegram работает."


def league_name_by_code(code: str, *, leagues: tuple[LeagueView, ...] = MVP_LEAGUES) -> str:
    for league in leagues:
        if league.code == code:
            return league.name
    return code


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "нет данных"
    return value.strftime("%d.%m %H:%M")
