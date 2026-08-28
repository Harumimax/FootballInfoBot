from __future__ import annotations

from datetime import date, datetime

from app.parser.dto import ParsedMatch, ParsedRound, ParsedStandingRow
from app.services.subscriptions.dto import LeagueView, StandingTableView, TeamSubscriptionView


NO_DATA_MESSAGE = "Данных пока нет."


MVP_LEAGUES: tuple[LeagueView, ...] = (
    LeagueView(code="england", name="Англия"),
    LeagueView(code="spain", name="Испания"),
)


def render_start_message() -> str:
    return (
        "FootballInfoBot присылает футбольные обновления по подписке.\n\n"
        "Сейчас можно подписаться на Англию, Испанию или команду из этих лиг, посмотреть таблицу и текущий тур."
    )


def render_help_message() -> str:
    return (
        "FootballInfoBot присылает футбольные обновления по подписке.\n\n"
        "Что можно сделать:\n"
        "- подписаться на Англию или Испанию;\n"
        "- подписаться на команду из Англии или Испании;\n"
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
        "Я работаю с личными подписками. Напишите мне в личный чат, чтобы выбрать подписки.\n\n"
        "Функционал для групповых чатов может появиться позже."
    )


def render_empty_subscriptions_message() -> str:
    return "У вас пока нет подписок."


def render_subscriptions_message(
    leagues: tuple[LeagueView, ...],
    team_subscriptions: tuple[TeamSubscriptionView, ...] = (),
) -> str:
    if not leagues and not team_subscriptions:
        return render_empty_subscriptions_message()

    lines = ["Ваши подписки:"]
    if leagues:
        lines.extend(("", "Лиги и турниры:"))
        lines.extend(league.name for league in leagues)
    if team_subscriptions:
        lines.extend(("", "Команды:"))
        lines.extend(f"{subscription.team.name} ({subscription.league.name})" for subscription in team_subscriptions)
    return "\n".join(lines)


def render_unsubscribed_message(league_name: str) -> str:
    return f"Вы отписались от {league_name}."


def render_team_subscription_changed_message(team_name: str, league_name: str, *, is_active: bool) -> str:
    if is_active:
        return f"Вы подписались на {team_name} ({league_name})."
    return f"Вы отписались от {team_name} ({league_name})."


def render_select_subscription_message() -> str:
    return "Что хотите выбрать для подписки?"


def render_select_league_subscription_message() -> str:
    return "Выберите лигу или турнир для подписки."


def render_select_team_league_message() -> str:
    return "Выберите лигу, чтобы посмотреть команды."


def render_select_team_message(league_name: str) -> str:
    return f"Выберите команду из лиги: {league_name}."


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


def render_rounds_state(league_name: str, rounds: tuple[ParsedRound, ...]) -> str:
    visible_rounds = tuple(round_ for round_ in rounds if round_.matches)
    if not visible_rounds:
        return NO_DATA_MESSAGE

    if len(visible_rounds) == 1:
        return render_round_state(league_name, visible_rounds[0])

    lines = [league_name]
    for round_ in visible_rounds:
        lines.extend(("", f"{round_.number}-й тур"))
        lines.extend(_format_match(match) for match in round_.matches)
    return "\n".join(lines)


def render_matchday_rounds_state(league_name: str, rounds: tuple[ParsedRound, ...], match_date: date) -> str:
    visible_rounds = tuple(round_ for round_ in rounds if round_.matches)
    if not visible_rounds:
        return NO_DATA_MESSAGE

    today_matches = [
        match
        for round_ in visible_rounds
        for match in round_.matches
        if match.scheduled_at is not None and match.scheduled_at.date() == match_date
    ]

    if not today_matches:
        return render_rounds_state(league_name, visible_rounds)

    lines = [league_name, "", "Матчи сегодня:"]
    for match in today_matches:
        lines.extend(_format_match_lines(match, include_goal_events=True))

    for round_ in visible_rounds:
        lines.extend(("", f"{round_.number}-й тур"))
        lines.extend(_format_match(match) for match in round_.matches)
    return "\n".join(lines)


def render_standings(table: StandingTableView | None) -> str:
    if table is None or not table.rows:
        return NO_DATA_MESSAGE

    lines = [f"{table.league.name}. Турнирная таблица", ""]
    lines.extend(_format_standing_row(row) for row in table.rows)
    return "\n".join(lines)


def _format_standing_row(row: ParsedStandingRow) -> str:
    details = [
        f"{row.played if row.played is not None else '-'} игр",
        f"{row.points if row.points is not None else '-'} очк.",
    ]

    if row.wins is not None and row.draws is not None and row.losses is not None:
        details.append(f"В{row.wins} Н{row.draws} П{row.losses}")

    if row.goals_for is not None and row.goals_against is not None:
        details.append(f"мячи {row.goals_for}-{row.goals_against}")

    return f"{row.position}. {row.team_name} - {', '.join(details)}"


def _format_match(match: ParsedMatch) -> str:
    date_time = _format_match_datetime(match.scheduled_at)
    if match.home_score is None or match.away_score is None:
        return f"{date_time} {match.home_team} - {match.away_team}"

    return f"{date_time} {match.home_team} {match.home_score}:{match.away_score} {match.away_team}"


def _format_match_lines(match: ParsedMatch, *, include_goal_events: bool) -> list[str]:
    lines = [_format_match(match)]
    if include_goal_events:
        lines.extend(f"{event.minute} {event.scorer_name}" for event in match.goal_events)
    return lines


def _format_match_datetime(value: datetime | None) -> str:
    if value is None:
        return "--.-- --:--"
    return value.strftime("%d.%m %H:%M")
