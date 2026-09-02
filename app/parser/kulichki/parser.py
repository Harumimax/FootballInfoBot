from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from app.parser.dto import LeaguePageData, ParsedGoalEvent, ParsedLeague, ParsedMatch, ParsedRound, ParsedStandingRow, RoundPageData


SOURCE_NAME = "kulichki"
ROUND_TITLE_RE = re.compile(r"(?P<number>\d+)\s*[-–]?\s*(?:й|ый|ой)?\s*тур", re.IGNORECASE)
SEASON_RE = re.compile(r"(?P<start>\d{4})\s*/\s*(?P<end>\d{4})")
SCORE_RE = re.compile(r"(?P<home>\d+)\s*[:\-]\s*(?P<away>\d+)")
TIME_RE = re.compile(r"(?P<hour>\d{1,2})[:\-](?P<minute>\d{2})")
GOAL_EVENT_RE = re.compile(
    r"(?P<scorer>[А-ЯЁA-Z][^.,\n]+?)\s*,\s*"
    r"(?P<minute>\d{1,3}(?:\+\d{1,2})?)"
    r"(?P<own_goal>\s*-\s*в\s+свои\s+ворота)?"
    r"\s*\((?P<score>\d+\s*[:\-]\s*\d+)\)",
    re.IGNORECASE,
)
DATE_TIME_RE = re.compile(
    r"(?P<day>\d{1,2})[.\-/](?P<month>\d{1,2})(?:[.\-/](?P<year>\d{2,4}))?\s+"
    r"(?P<hour>\d{1,2})[:\-](?P<minute>\d{2})"
)
RUSSIAN_DATE_RE = re.compile(r"(?P<day>\d{1,2})\s+(?P<month>[а-яё]+)", re.IGNORECASE)
RUSSIAN_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


class KulichkiParser:
    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/") + "/"

    def parse_league_page(self, html: str, *, url: str, league_code: str, league_name: str) -> LeaguePageData:
        soup = BeautifulSoup(html, "html.parser")
        season_label, season_key = _extract_season(soup.get_text(" ", strip=True))
        season_start_year, season_end_year = _extract_season_years(season_label)
        current_round_number = _extract_current_round_number(soup)
        round_url = _extract_current_round_url(soup, url, current_round_number, season_key)
        visible_rounds = _extract_visible_rounds(
            soup,
            page_url=url,
            season_key=season_key,
            season_start_year=season_start_year,
            season_end_year=season_end_year,
        )
        standings = _extract_standings(soup)

        current_round = None
        if visible_rounds:
            current_round = next(
                (round_ for round_ in visible_rounds if round_.number == current_round_number),
                visible_rounds[0],
            )
        elif current_round_number is not None:
            matches = _extract_matches(
                soup,
                page_url=url,
                round_number=current_round_number,
                season_start_year=season_start_year,
                season_end_year=season_end_year,
            )
            current_round = ParsedRound(
                number=current_round_number,
                source_url=round_url,
                matches=tuple(matches),
            )
            visible_rounds = (current_round,)

        return LeaguePageData(
            league=ParsedLeague(code=league_code, name=league_name, source_url=url),
            season_label=season_label,
            source_season_key=season_key,
            current_round=current_round,
            standings=tuple(standings),
            rounds=tuple(visible_rounds),
        )

    def parse_round_page(self, html: str, *, url: str, league_code: str, league_name: str) -> RoundPageData:
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(" ", strip=True)
        season_label, season_key = _extract_season(page_text)
        season_start_year, season_end_year = _extract_season_years(season_label)
        round_number = _extract_current_round_number(soup)

        if round_number is None:
            raise ValueError("Could not detect round number on Kulichki round page")

        return RoundPageData(
            league=ParsedLeague(code=league_code, name=league_name, source_url=_league_url_from_round_url(url)),
            season_label=season_label,
            source_season_key=season_key,
            round=ParsedRound(
                number=round_number,
                source_url=url,
                matches=tuple(
                    _extract_matches(
                        soup,
                        page_url=url,
                        round_number=round_number,
                        season_start_year=season_start_year,
                        season_end_year=season_end_year,
                    )
                ),
            ),
        )

    def parse_match_page(self, html: str, *, url: str) -> tuple[ParsedGoalEvent, ...]:
        soup = BeautifulSoup(html, "html.parser")
        return tuple(_extract_goal_events(soup))


def _extract_season(text: str) -> tuple[str | None, str | None]:
    match = SEASON_RE.search(text)
    if match is None:
        return None, None
    label = f"{match.group('start')}/{match.group('end')}"
    return label, match.group("end")


def _extract_season_years(season_label: str | None) -> tuple[int | None, int | None]:
    if season_label is None:
        return None, None
    match = SEASON_RE.match(season_label)
    if match is None:
        return None, None
    return int(match.group("start")), int(match.group("end"))


def _extract_current_round_number(soup: BeautifulSoup) -> int | None:
    explicit = soup.select_one("[data-current-round]")
    if explicit is not None:
        raw_value = explicit.get("data-current-round", "").strip()
        if raw_value.isdigit():
            return int(raw_value)

    candidates = []
    for selector in ("h1", "h2", "h3", ".current-round", ".tour", ".round"):
        candidates.extend(soup.select(selector))

    for candidate in candidates:
        number = _round_number_from_text(candidate.get_text(" ", strip=True))
        if number is not None:
            return number

    return _round_number_from_text(soup.get_text(" ", strip=True))


def _round_number_from_text(text: str) -> int | None:
    match = ROUND_TITLE_RE.search(text)
    if match is None:
        return None
    return int(match.group("number"))


def _extract_current_round_url(
    soup: BeautifulSoup,
    page_url: str,
    round_number: int | None,
    season_key: str | None,
) -> str | None:
    if round_number is None:
        return None

    if season_key is not None:
        parsed = urlparse(page_url)
        league_path = [part for part in parsed.path.split("/") if part]
        if league_path:
            return f"{parsed.scheme}://{parsed.netloc}/{league_path[0]}/{season_key}/{round_number}/"

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(" ", strip=True)
        href_path = urlparse(urljoin(page_url, link["href"])).path.rstrip("/")
        if href_path.endswith(f"/{round_number}") or _round_number_from_text(link_text) == round_number:
            return urljoin(page_url, link["href"])

    return None


def _extract_visible_rounds(
    soup: BeautifulSoup,
    *,
    page_url: str,
    season_key: str | None,
    season_start_year: int | None,
    season_end_year: int | None,
) -> tuple[ParsedRound, ...]:
    round_matches: dict[int, list[ParsedMatch]] = {}
    round_urls: dict[int, str | None] = {}
    active_round_number: int | None = None

    for tr in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"], recursive=False)]
        row_text = " ".join(cells)
        detected_round_number = _round_number_from_text(row_text)
        if detected_round_number is not None:
            active_round_number = detected_round_number
            round_matches.setdefault(active_round_number, [])
            round_urls.setdefault(active_round_number, _round_url(page_url, active_round_number, season_key))
            continue

        if active_round_number is None:
            continue

        match = _parse_match_cells(
            cells,
            source_url=_extract_match_source_link(tr, page_url=page_url),
            row=tr,
            season_start_year=season_start_year,
            season_end_year=season_end_year,
        )
        if match is None:
            continue
        match_round_number = _round_number_from_match_url(match.source_url, season_key) or active_round_number
        if match_round_number is None or not _match_belongs_to_round(match, match_round_number):
            continue
        round_matches.setdefault(match_round_number, []).append(match)
        round_urls.setdefault(match_round_number, _round_url(page_url, match_round_number, season_key))

    rounds = []
    for round_number, matches in round_matches.items():
        unique_matches = _deduplicate_matches(matches)
        if not unique_matches:
            continue
        rounds.append(
            ParsedRound(
                number=round_number,
                source_url=round_urls.get(round_number),
                matches=tuple(unique_matches),
            )
        )
    return tuple(rounds)


def _round_url(page_url: str, round_number: int, season_key: str | None) -> str | None:
    if season_key is None:
        return None
    parsed = urlparse(page_url)
    league_path = [part for part in parsed.path.split("/") if part]
    if not league_path:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/{league_path[0]}/{season_key}/{round_number}/"


def _extract_matches(
    soup: BeautifulSoup,
    *,
    page_url: str,
    round_number: int | None,
    season_start_year: int | None,
    season_end_year: int | None,
) -> list[ParsedMatch]:
    rows = []

    for row in soup.select("[data-match]"):
        if isinstance(row, Tag):
            match = _parse_structured_match(row, page_url=page_url, season_start_year=season_start_year)
            if match is not None:
                if not _match_belongs_to_round(match, round_number):
                    continue
                rows.append(match)

    if rows:
        return rows

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"], recursive=False)]
            match = _parse_match_cells(
                cells,
                source_url=_extract_match_source_link(tr, page_url=page_url),
                row=tr,
                season_start_year=season_start_year,
                season_end_year=season_end_year,
            )
            if match is not None:
                if not _match_belongs_to_round(match, round_number):
                    continue
                rows.append(match)

    return _deduplicate_matches(rows)


def _parse_structured_match(
    row: Tag,
    *,
    page_url: str,
    season_start_year: int | None,
) -> ParsedMatch | None:
    date_text = _select_text(row, "[data-match-date], .date")
    time_text = _select_text(row, "[data-match-time], .time")
    home_team = _select_text(row, "[data-home-team], .home")
    away_team = _select_text(row, "[data-away-team], .away")
    score_text = _select_text(row, "[data-score], .score")
    status = _select_text(row, "[data-status], .status") or "unknown"

    if not home_team or not away_team:
        return None

    scheduled_at = _parse_datetime(f"{date_text} {time_text}".strip(), default_year=season_start_year)
    home_score, away_score = _parse_score(score_text)

    return ParsedMatch(
        home_team=home_team,
        away_team=away_team,
        scheduled_at=scheduled_at,
        home_score=home_score,
        away_score=away_score,
        status=_normalize_status(status, home_score, away_score),
        source_url=_extract_first_link(row, page_url=page_url),
    )


def _parse_match_cells(
    cells: list[str],
    *,
    source_url: str | None,
    row: Tag | None,
    season_start_year: int | None,
    season_end_year: int | None,
) -> ParsedMatch | None:
    if len(cells) < 3:
        return None

    home_team = ""
    away_team = ""
    if row is not None and _looks_like_kulichki_match_row(cells):
        team_links = _extract_team_links(row)
        if len(team_links) >= 2:
            home_team, away_team = team_links[0], team_links[1]

    score_text = ""
    scheduled_at = None

    if home_team and away_team:
        score_text = cells[2]
        scheduled_at = _parse_kulichki_match_datetime(
            date_text=cells[0],
            result_text=cells[2],
            season_start_year=season_start_year,
            season_end_year=season_end_year,
        )
    else:
        joined = " ".join(cells)
        if not DATE_TIME_RE.search(joined):
            return None

        if len(cells) >= 5:
            home_team = cells[2]
            score_text = cells[3]
            away_team = cells[4]
        elif len(cells) == 4:
            home_team = cells[1]
            score_text = cells[2]
            away_team = cells[3]
        scheduled_at = _parse_datetime(joined, default_year=season_start_year)

    if not home_team or not away_team:
        return None

    home_score, away_score = _parse_score(score_text)

    return ParsedMatch(
        home_team=_clean_team_name(home_team),
        away_team=_clean_team_name(away_team),
        scheduled_at=scheduled_at,
        home_score=home_score,
        away_score=away_score,
        status=_normalize_status(score_text, home_score, away_score),
        source_url=source_url,
    )


def _looks_like_kulichki_match_row(cells: list[str]) -> bool:
    if len(cells) != 4:
        return False
    return RUSSIAN_DATE_RE.fullmatch(cells[0].strip()) is not None and " - " in cells[1]


def _extract_team_links(row: Tag) -> list[str]:
    names = []
    for link in row.find_all("a", href=True):
        href = link.get("href", "")
        if "/teams/" not in href:
            continue
        name = _clean_team_name(link.get_text(" ", strip=True))
        if name:
            names.append(name)
    return names


def _parse_kulichki_match_datetime(
    *,
    date_text: str,
    result_text: str,
    season_start_year: int | None,
    season_end_year: int | None,
) -> datetime | None:
    date_match = RUSSIAN_DATE_RE.fullmatch(date_text.strip())
    time_match = TIME_RE.search(result_text)
    if date_match is None:
        return None

    month = RUSSIAN_MONTHS.get(date_match.group("month").lower())
    if month is None:
        return None

    year = _season_year_for_month(month, season_start_year, season_end_year)
    hour = int(time_match.group("hour")) if time_match is not None else 0
    minute = int(time_match.group("minute")) if time_match is not None else 0
    return datetime(
        year=year,
        month=month,
        day=int(date_match.group("day")),
        hour=hour,
        minute=minute,
    )


def _season_year_for_month(month: int, season_start_year: int | None, season_end_year: int | None) -> int:
    if season_start_year is None:
        return datetime.now().year
    if season_end_year is None:
        return season_start_year
    return season_start_year if month >= 7 else season_end_year


def _extract_standings(soup: BeautifulSoup) -> list[ParsedStandingRow]:
    rows = []

    for row in soup.select("[data-standing-row]"):
        if not isinstance(row, Tag):
            continue
        position = _parse_int(_select_text(row, "[data-position], .position"))
        team_name = _select_text(row, "[data-team], .team")
        if position is None or not team_name:
            continue
        rows.append(
            ParsedStandingRow(
                position=position,
                team_name=team_name,
                played=_parse_int(_select_text(row, "[data-played], .played")),
                points=_parse_int(_select_text(row, "[data-points], .points")),
                wins=_parse_int(_select_text(row, "[data-wins], .wins")),
                draws=_parse_int(_select_text(row, "[data-draws], .draws")),
                losses=_parse_int(_select_text(row, "[data-losses], .losses")),
                goals_for=_parse_int(_select_text(row, "[data-goals-for], .goals-for")),
                goals_against=_parse_int(_select_text(row, "[data-goals-against], .goals-against")),
            )
        )

    if rows:
        return rows

    for table in soup.find_all("table"):
        if not _looks_like_standings_table(table):
            continue
        for tr in table.find_all("tr"):
            cells = [
                _clean_team_name(cell.get_text(" ", strip=True))
                for cell in tr.find_all(["td", "th"], recursive=False)
            ]
            cells = [cell for cell in cells if cell]
            if len(cells) < 4:
                continue
            position = _parse_int(cells[0])
            if position is None:
                continue
            goals_for, goals_against = _parse_goals_pair(cells[6]) if len(cells) >= 8 else (None, None)
            rows.append(
                ParsedStandingRow(
                    position=position,
                    team_name=_clean_team_name(cells[1]),
                    played=_parse_int(cells[2]),
                    wins=_parse_int(cells[3]) if len(cells) >= 8 else None,
                    draws=_parse_int(cells[4]) if len(cells) >= 8 else None,
                    losses=_parse_int(cells[5]) if len(cells) >= 8 else None,
                    goals_for=goals_for,
                    goals_against=goals_against,
                    goal_difference=_parse_goal_difference(cells[6]) if len(cells) >= 8 else None,
                    points=_parse_int(cells[-1]),
                )
            )

    return rows


def _looks_like_standings_table(table: Tag) -> bool:
    for tr in table.find_all("tr"):
        cells = [
            _normalize_standings_header_cell(cell.get_text(" ", strip=True))
            for cell in tr.find_all(["td", "th"], recursive=False)
        ]
        cells = [cell for cell in cells if cell]
        if not cells:
            continue
        has_team_header = any(cell in {"клуб", "команда", "team"} for cell in cells)
        has_points_header = any(cell in {"о", "очк", "очки", "points"} or cell.startswith("очк") for cell in cells)
        if has_team_header and has_points_header:
            return True

    table_text = table.get_text(" ", strip=True).lower()
    has_team_word = any(marker in table_text for marker in ("клуб", "команда", "team"))
    has_points_word = any(marker in table_text for marker in ("очк", "points"))
    return has_team_word and has_points_word


def _normalize_standings_header_cell(value: str) -> str:
    return _clean_team_name(value).replace("№", "n").lower()


def _select_text(row: Tag, selector: str) -> str:
    node = row.select_one(selector)
    return node.get_text(" ", strip=True) if node is not None else ""


def _parse_datetime(text: str, *, default_year: int | None = None) -> datetime | None:
    match = DATE_TIME_RE.search(text)
    if match is None:
        return None

    year_text = match.group("year")
    if year_text is None:
        year = default_year if default_year is not None else datetime.now().year
    elif len(year_text) == 2:
        year = 2000 + int(year_text)
    else:
        year = int(year_text)

    return datetime(
        year=year,
        month=int(match.group("month")),
        day=int(match.group("day")),
        hour=int(match.group("hour")),
        minute=int(match.group("minute")),
    )


def _parse_score(text: str) -> tuple[int | None, int | None]:
    cleaned = text.strip()
    if TIME_RE.fullmatch(cleaned):
        return None, None
    match = SCORE_RE.search(cleaned)
    if match is None:
        return None, None
    return int(match.group("home")), int(match.group("away"))


def _normalize_status(raw_status: str, home_score: int | None, away_score: int | None) -> str:
    normalized = raw_status.strip().lower()
    if home_score is not None and away_score is not None:
        return "finished"
    if any(marker in normalized for marker in ("live", "ид", "перерыв")):
        return "live"
    if any(marker in normalized for marker in ("перен", "отлож", "postpon")):
        return "postponed"
    return "scheduled"


def _parse_int(value: str) -> int | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    match = re.search(r"\d+", cleaned)
    return int(match.group(0)) if match else None


def _parse_goals_pair(value: str) -> tuple[int | None, int | None]:
    match = SCORE_RE.search(value.strip())
    if match is None:
        return None, None
    return int(match.group("home")), int(match.group("away"))


def _parse_goal_difference(value: str) -> int | None:
    goals_for, goals_against = _parse_goals_pair(value)
    if goals_for is None or goals_against is None:
        return None
    return goals_for - goals_against


def _extract_goal_events(soup: BeautifulSoup) -> list[ParsedGoalEvent]:
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if SCORE_RE.search(line) is None:
            continue
        if " - " not in line:
            continue
        events = _parse_goal_events_line(" ".join(lines[index + 1 : index + 8]))
        if events:
            return events
    return []


def _parse_goal_events_line(line: str) -> list[ParsedGoalEvent]:
    events = []
    for position, match in enumerate(GOAL_EVENT_RE.finditer(line), start=1):
        events.append(
            ParsedGoalEvent(
                minute=match.group("minute"),
                scorer_name=_clean_team_name(match.group("scorer")),
                score_after=match.group("score").replace("-", ":").replace(" ", ""),
                position=position,
                is_own_goal=bool(match.group("own_goal")),
            )
        )
    return events


def _extract_first_link(row: Tag, *, page_url: str) -> str | None:
    link = row.find("a", href=True)
    return urljoin(page_url, link["href"]) if link is not None else None


def _extract_match_source_link(row: Tag, *, page_url: str) -> str | None:
    for link in row.find_all("a", href=True):
        href = link["href"]
        if "/teams/" in href or "/trans/" in href:
            continue
        return urljoin(page_url, href)
    return _extract_first_link(row, page_url=page_url)


def _clean_team_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _deduplicate_matches(matches: list[ParsedMatch]) -> list[ParsedMatch]:
    seen = set()
    unique = []
    for match in matches:
        key = (match.scheduled_at, match.home_team, match.away_team)
        if key in seen:
            continue
        seen.add(key)
        unique.append(match)
    return unique


def _match_belongs_to_round(match: ParsedMatch, round_number: int | None) -> bool:
    if round_number is None or match.source_url is None:
        return True
    path = urlparse(match.source_url).path
    return f"/{round_number}/" in path or path.rstrip("/").endswith(f"/{round_number}")


def _round_number_from_match_url(source_url: str | None, season_key: str | None) -> int | None:
    if source_url is None or season_key is None:
        return None
    parts = [part for part in urlparse(source_url).path.split("/") if part]
    for index, part in enumerate(parts):
        if part == season_key and index + 1 < len(parts) and parts[index + 1].isdigit():
            return int(parts[index + 1])
    return None


def _league_url_from_round_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return url
    return f"{parsed.scheme}://{parsed.netloc}/{parts[0]}/"
