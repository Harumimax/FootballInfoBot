from __future__ import annotations

from datetime import datetime

from app.bot.messages.rendering import LeagueView, MVP_LEAGUES
from app.services.admin.dto import AdminSyncResult, LeagueParserStatusView, LeagueToggleResult, ParserStatusView


NO_PARSER_ERROR_MESSAGE = "Ошибок парсера пока нет."


def render_admin_menu_message() -> str:
    return "Админка FootballInfoBot."


def render_admin_sync_select_message() -> str:
    return "Выберите лигу для принудительного обновления."


def render_admin_toggle_select_message() -> str:
    return "Выберите лигу, которую нужно включить или отключить."


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


def league_name_by_code(code: str, *, leagues: tuple[LeagueView, ...] = MVP_LEAGUES) -> str:
    for league in leagues:
        if league.code == code:
            return league.name
    return code


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "нет данных"
    return value.strftime("%d.%m %H:%M")
