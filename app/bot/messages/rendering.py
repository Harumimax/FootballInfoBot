from __future__ import annotations

from datetime import datetime

from app.parser.dto import ParsedMatch, ParsedRound
from app.services.subscriptions.dto import StandingTableView
from app.services.subscriptions.dto import LeagueView


NO_DATA_MESSAGE = "Данных пока нет."


MVP_LEAGUES: tuple[LeagueView, ...] = (
    LeagueView(code="england", name="Англия"),
    LeagueView(code="spain", name="Испания"),
)


def render_start_message() -> str:
    return (
        "FootballInfoBot присылает футбольные обновления по подписке.\n\n"
        "Сейчас можно подписаться на Англию или Испанию, посмотреть таблицу и текущий тур."
    )


def render_help_message() -> str:
    return (
        "FootballInfoBot присылает футбольные обновления по подписке.\n\n"
        "Что можно сделать:\n"
        "- подписаться на Англию или Испанию;\n"
        "- посмотреть свои подписки;\n"
        "- запросить турнирную таблицу;\n"
        "- запросить текущий тур.\n\n"
        "Автоуведомления приходят только в дни матчей:\n"
        "- утром около 09:00;\n"
        "- после завершения матчей дня.\n\n"
        f"Если данных нет, бот напишет: {NO_DATA_MESSAGE}\n\n"
        "Источник данных: football.kulichki.net.\n"
        "Бот не является официальным сервисом football.kulichki.net."
    )


def render_group_not_supported_message() -> str:
    return (
        "Я работаю с личными подписками. Напишите мне в личный чат, чтобы выбрать лиги.\n\n"
        "Функционал для групповых чатов может появиться позже."
    )


def render_empty_subscriptions_message() -> str:
    return "У вас пока нет подписок."


def render_subscriptions_message(leagues: tuple[LeagueView, ...]) -> str:
    if not leagues:
        return render_empty_subscriptions_message()

    league_lines = "\n".join(league.name for league in leagues)
    return f"Ваши подписки:\n\n{league_lines}"


def render_unsubscribed_message(league_name: str) -> str:
    return f"Вы отписались от {league_name}."


def render_select_subscription_message() -> str:
    return "Выберите лигу или турнир для подписки."


def render_select_league_for_table_message() -> str:
    return "Выберите лигу, чтобы посмотреть турнирную таблицу."


def render_select_league_for_round_message() -> str:
    return "Выберите лигу, чтобы посмотреть текущий тур."


def render_round_state(league_name: str, round_: ParsedRound | None) -> str:
    if round_ is None or not round_.matches:
        return NO_DATA_MESSAGE

    lines = [f"{league_name}, {round_.number}-й тур", ""]
    lines.extend(_format_match(match) for match in round_.matches)
    return "\n".join(lines)


def render_standings(table: StandingTableView | None) -> str:
    if table is None or not table.rows:
        return NO_DATA_MESSAGE

    lines = [f"{table.league.name}. Турнирная таблица", ""]
    lines.extend(
        f"{row.position}. {row.team_name} - {row.points if row.points is not None else '-'} очк. ({row.played if row.played is not None else '-'} игр)"
        for row in table.rows
    )
    return "\n".join(lines)


def _format_match(match: ParsedMatch) -> str:
    date_time = _format_match_datetime(match.scheduled_at)
    if match.home_score is None or match.away_score is None:
        return f"{date_time} {match.home_team} - {match.away_team}"

    return f"{date_time} {match.home_team} {match.home_score}:{match.away_score} {match.away_team}"


def _format_match_datetime(value: datetime | None) -> str:
    if value is None:
        return "--.-- --:--"
    return value.strftime("%d.%m %H:%M")
