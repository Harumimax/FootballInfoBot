from __future__ import annotations

from datetime import date, datetime
from html import escape

from app.parser.dto import ParsedGoalEvent, ParsedMatch, ParsedRound, ParsedStandingRow
from app.services.subscriptions.dto import LeagueView, StandingTableView, TeamSubscriptionView


USER_MESSAGE_PARSE_MODE = "HTML"
NO_DATA_MESSAGE = "⏳ <b>Данных пока нет</b>\n\nПопробуйте чуть позже."

LEAGUE_FLAGS = {
    "Лига чемпионов": "🏆",
    "Лига Европы": "🌍",
    "Лига конференций": "🔷",
    "Англия": "🇬🇧",
    "Испания": "🇪🇸",
    "Германия": "🇩🇪",
    "Италия": "🇮🇹",
    "Франция": "🇫🇷",
    "Россия": "🇷🇺",
}


MVP_LEAGUES: tuple[LeagueView, ...] = (
    LeagueView(code="league", name="Лига чемпионов"),
    LeagueView(code="uefa_cup", name="Лига Европы"),
    LeagueView(code="lc", name="Лига конференций"),
    LeagueView(code="england", name="Англия"),
    LeagueView(code="spain", name="Испания"),
    LeagueView(code="germany", name="Германия"),
    LeagueView(code="italy", name="Италия"),
    LeagueView(code="france", name="Франция"),
    LeagueView(code="ruschamp", name="Россия"),
)


def render_start_message() -> str:
    return (
        "⚽ <b>FootballInfoBot</b>\n\n"
        "Я слежу за футбольными лигами и командами:\n"
        "• матчи тура\n"
        "• матчи любимых команд\n"
        "• результаты после игрового дня\n"
        "• турнирные таблицы\n\n"
        "Можно подписаться на Лигу чемпионов, Лигу Европы, Лигу конференций, "
        "Англию, Испанию, Германию, Италию, Францию, Россию или любимую команду.\n\n"
        "Доступны: 🏆 Лига чемпионов, 🌍 Лига Европы, 🔷 Лига конференций, "
        "🇬🇧 Англия, 🇪🇸 Испания, 🇩🇪 Германия, 🇮🇹 Италия, 🇫🇷 Франция, 🇷🇺 Россия.\n\n"
        "Выберите, что хотите получать."
    )


def render_help_message() -> str:
    return (
        "⚽ <b>FootballInfoBot</b>\n\n"
        "Что можно сделать:\n"
        "• подписаться на лигу, турнир или команду\n"
        "• посмотреть свои подписки\n"
        "• запросить турнирную таблицу\n"
        "• запросить текущий тур\n\n"
        "🔔 Автоуведомления приходят только в дни матчей:\n"
        "• утром около 09:00\n"
        "• после завершения матчей дня\n\n"
        "Источник данных: football.kulichki.net.\n"
        "Бот не является официальным сервисом football.kulichki.net."
    )


def render_group_not_supported_message() -> str:
    return (
        "💬 Я работаю с личными подписками.\n\n"
        "Напишите мне в личный чат, чтобы выбрать лиги и команды.\n"
        "Функционал для групповых чатов может появиться позже."
    )


def render_empty_subscriptions_message() -> str:
    return "🔕 <b>У вас пока нет подписок</b>\n\nМожно подписаться на лигу, турнир или команду."


def render_subscriptions_message(
    leagues: tuple[LeagueView, ...],
    team_subscriptions: tuple[TeamSubscriptionView, ...] = (),
) -> str:
    if not leagues and not team_subscriptions:
        return render_empty_subscriptions_message()

    lines = ["🔔 <b>Ваши подписки</b>", ""]
    if leagues:
        lines.append("🏆 <b>Лиги и турниры:</b>")
        lines.extend(f"✅ {_format_league_name(league.name)}" for league in leagues)
        lines.append("")
    if team_subscriptions:
        lines.append("⭐ <b>Команды:</b>")
        lines.extend(
            f"✅ {escape(subscription.team.name)} ({_format_league_name(subscription.league.name)})"
            for subscription in team_subscriptions
        )
        lines.append("")
    lines.append("Нажмите на подписку, чтобы отключить её.")
    return "\n".join(lines)


def render_unsubscribed_message(league_name: str) -> str:
    return f"🔕 Вы отписались от {escape(league_name)}."


def render_team_subscription_changed_message(team_name: str, league_name: str, *, is_active: bool) -> str:
    if is_active:
        return f"✅ Вы подписались на {escape(team_name)} ({_format_league_name(league_name)})."
    return f"🔕 Вы отписались от {escape(team_name)} ({_format_league_name(league_name)})."


def render_select_subscription_message() -> str:
    return "🎯 <b>Что хотите выбрать для подписки?</b>"


def render_select_league_subscription_message() -> str:
    return "🏆 <b>Выберите лигу или турнир для подписки</b>"


def render_select_team_league_message() -> str:
    return "⭐ <b>Выберите лигу, чтобы посмотреть команды</b>"


def render_select_team_message(league_name: str) -> str:
    return f"⭐ <b>Выберите команду</b>\n\nЛига: {_format_league_name(league_name)}"


def render_select_league_for_table_message() -> str:
    return "📊 <b>Выберите лигу, чтобы посмотреть турнирную таблицу</b>"


def render_select_league_for_round_message() -> str:
    return "🏟️ <b>Выберите лигу, чтобы посмотреть текущий тур</b>"


def render_round_state(league_name: str, round_: ParsedRound | None) -> str:
    if round_ is None or not round_.matches:
        return NO_DATA_MESSAGE

    lines = [_format_league_title(league_name), f"🏆 <b>{round_.number}-й тур</b>", ""]
    lines.extend(_format_match(match) for match in round_.matches)
    return "\n".join(lines)


def render_rounds_state(league_name: str, rounds: tuple[ParsedRound, ...]) -> str:
    visible_rounds = tuple(round_ for round_ in rounds if round_.matches)
    if not visible_rounds:
        return NO_DATA_MESSAGE

    if len(visible_rounds) == 1:
        return render_round_state(league_name, visible_rounds[0])

    lines = [_format_league_title(league_name)]
    for index, round_ in enumerate(visible_rounds):
        lines.extend(("", _format_round_title(round_.number, is_primary=index == 0)))
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

    header_lines = _format_matchday_header(league_name)
    lines = [*header_lines, "", "📅 <b>Матчи сегодня</b>"]
    for match in today_matches:
        lines.extend(_format_match_lines(match, include_goal_events=True))

    for index, round_ in enumerate(visible_rounds):
        lines.extend(("", _format_round_title(round_.number, is_primary=index == 0)))
        lines.extend(_format_match(match) for match in round_.matches)
    return "\n".join(lines)


def render_standings(table: StandingTableView | None) -> str:
    if table is None or not table.rows:
        return NO_DATA_MESSAGE

    lines = [f"📊 {_format_league_name(table.league.name)}. <b>Турнирная таблица</b>", ""]
    lines.extend(_format_standing_row(row) for row in table.rows)
    return "\n".join(lines)


def _format_standing_row(row: ParsedStandingRow) -> str:
    played = row.played if row.played is not None else "-"
    points = row.points if row.points is not None else "-"
    return f"{row.position}. {escape(row.team_name)} — {played} игр, {points} очк."


def _format_match(match: ParsedMatch) -> str:
    date_time = _format_match_datetime(match.scheduled_at)
    if match.home_score is None or match.away_score is None:
        return f"{date_time} {escape(match.home_team)} - {escape(match.away_team)}"

    return f"{date_time} {escape(match.home_team)} <b>{match.home_score}:{match.away_score}</b> {escape(match.away_team)}"


def _format_match_lines(match: ParsedMatch, *, include_goal_events: bool) -> list[str]:
    lines = [_format_match(match)]
    if include_goal_events:
        lines.extend(_format_goal_event(event) for event in match.goal_events)
    return lines


def _format_goal_event(event: ParsedGoalEvent) -> str:
    suffix = " (АГ)" if event.is_own_goal else ""
    return f"  ⚽ {escape(event.minute)} {escape(event.scorer_name)}{suffix}"


def _format_match_datetime(value: datetime | None) -> str:
    if value is None:
        return "--.-- --:--"
    return value.strftime("%d.%m %H:%M")


def _format_league_title(league_name: str) -> str:
    return f"{_league_flag(league_name)} <b>{escape(league_name)}</b>"


def _format_league_name(league_name: str) -> str:
    return f"{_league_flag(league_name)} {escape(league_name)}"


def _format_round_title(round_number: int, *, is_primary: bool) -> str:
    icon = "🏆" if is_primary else "↩️"
    return f"{icon} <b>{round_number}-й тур</b>"


def _format_matchday_header(league_name: str) -> list[str]:
    league, team = _split_team_league_title(league_name)
    if team is None:
        return [_format_league_title(league)]
    return [f"⭐ <b>{escape(team)}</b>", _format_league_name(league)]


def _split_team_league_title(value: str) -> tuple[str, str | None]:
    if ". " not in value:
        return value, None
    league, team = value.split(". ", maxsplit=1)
    return league, team


def _league_flag(league_name: str) -> str:
    league, _ = _split_team_league_title(league_name)
    return LEAGUE_FLAGS.get(league, "🏳️")
