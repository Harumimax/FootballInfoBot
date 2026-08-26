from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from app.parser.dto import LeaguePageData, ParsedLeague, ParsedMatch, ParsedRound, ParsedStandingRow, RoundPageData


SOURCE_NAME = "kulichki"
ROUND_TITLE_RE = re.compile(r"(?P<number>\d+)\s*[-–]?\s*(?:й|ый|ой)?\s*тур", re.IGNORECASE)
SEASON_RE = re.compile(r"(?P<start>\d{4})\s*/\s*(?P<end>\d{4})")
SCORE_RE = re.compile(r"^(?P<home>\d+)\s*[:\-]\s*(?P<away>\d+)$")
DATE_TIME_RE = re.compile(
    r"(?P<day>\d{1,2})[.\-/](?P<month>\d{1,2})(?:[.\-/](?P<year>\d{2,4}))?\s+"
    r"(?P<hour>\d{1,2})[:\-](?P<minute>\d{2})"
)


class KulichkiParser:
    def __init__(self, *, base_url: str) -> None:
        self._base_url = base_url.rstrip("/") + "/"

    def parse_league_page(self, html: str, *, url: str, league_code: str, league_name: str) -> LeaguePageData:
        soup = BeautifulSoup(html, "html.parser")
        season_label, season_key = _extract_season(soup.get_text(" ", strip=True))
        current_round_number = _extract_current_round_number(soup)
        round_url = _extract_current_round_url(soup, url, current_round_number)
        matches = _extract_matches(soup)
        standings = _extract_standings(soup)

        current_round = None
        if current_round_number is not None:
            current_round = ParsedRound(
                number=current_round_number,
                source_url=round_url,
                matches=tuple(matches),
            )

        return LeaguePageData(
            league=ParsedLeague(code=league_code, name=league_name, source_url=url),
            season_label=season_label,
            source_season_key=season_key,
            current_round=current_round,
            standings=tuple(standings),
        )

    def parse_round_page(self, html: str, *, url: str, league_code: str, league_name: str) -> RoundPageData:
        soup = BeautifulSoup(html, "html.parser")
        page_text = soup.get_text(" ", strip=True)
        season_label, season_key = _extract_season(page_text)
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
                matches=tuple(_extract_matches(soup)),
            ),
        )


def _extract_season(text: str) -> tuple[str | None, str | None]:
    match = SEASON_RE.search(text)
    if match is None:
        return None, None
    label = f"{match.group('start')}/{match.group('end')}"
    return label, match.group("end")


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


def _extract_current_round_url(soup: BeautifulSoup, page_url: str, round_number: int | None) -> str | None:
    if round_number is None:
        return None

    for link in soup.find_all("a", href=True):
        link_text = link.get_text(" ", strip=True)
        if str(round_number) not in link_text and _round_number_from_text(link_text) != round_number:
            continue
        return urljoin(page_url, link["href"])

    return None


def _extract_matches(soup: BeautifulSoup) -> list[ParsedMatch]:
    rows = []

    for row in soup.select("[data-match]"):
        if isinstance(row, Tag):
            match = _parse_structured_match(row)
            if match is not None:
                rows.append(match)

    if rows:
        return rows

    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
            match = _parse_match_cells(cells, source_url=_extract_first_link(tr))
            if match is not None:
                rows.append(match)

    return rows


def _parse_structured_match(row: Tag) -> ParsedMatch | None:
    date_text = _select_text(row, "[data-match-date], .date")
    time_text = _select_text(row, "[data-match-time], .time")
    home_team = _select_text(row, "[data-home-team], .home")
    away_team = _select_text(row, "[data-away-team], .away")
    score_text = _select_text(row, "[data-score], .score")
    status = _select_text(row, "[data-status], .status") or "unknown"

    if not home_team or not away_team:
        return None

    scheduled_at = _parse_datetime(f"{date_text} {time_text}".strip())
    home_score, away_score = _parse_score(score_text)

    return ParsedMatch(
        home_team=home_team,
        away_team=away_team,
        scheduled_at=scheduled_at,
        home_score=home_score,
        away_score=away_score,
        status=_normalize_status(status, home_score, away_score),
        source_url=_extract_first_link(row),
    )


def _parse_match_cells(cells: list[str], *, source_url: str | None) -> ParsedMatch | None:
    if len(cells) < 3:
        return None

    joined = " ".join(cells)
    if not DATE_TIME_RE.search(joined):
        return None

    home_team = ""
    away_team = ""
    score_text = ""

    if len(cells) >= 5:
        home_team = cells[2]
        score_text = cells[3]
        away_team = cells[4]
    elif len(cells) == 4:
        home_team = cells[1]
        score_text = cells[2]
        away_team = cells[3]

    if not home_team or not away_team:
        return None

    scheduled_at = _parse_datetime(joined)
    home_score, away_score = _parse_score(score_text)

    return ParsedMatch(
        home_team=home_team,
        away_team=away_team,
        scheduled_at=scheduled_at,
        home_score=home_score,
        away_score=away_score,
        status=_normalize_status(score_text, home_score, away_score),
        source_url=source_url,
    )


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
            )
        )

    if rows:
        return rows

    for table in soup.find_all("table"):
        table_text = table.get_text(" ", strip=True).lower()
        if "очк" not in table_text and "points" not in table_text:
            continue
        for tr in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["td", "th"])]
            if len(cells) < 4:
                continue
            position = _parse_int(cells[0])
            if position is None:
                continue
            rows.append(
                ParsedStandingRow(
                    position=position,
                    team_name=cells[1],
                    played=_parse_int(cells[2]),
                    points=_parse_int(cells[-1]),
                )
            )

    return rows


def _select_text(row: Tag, selector: str) -> str:
    node = row.select_one(selector)
    return node.get_text(" ", strip=True) if node is not None else ""


def _parse_datetime(text: str) -> datetime | None:
    match = DATE_TIME_RE.search(text)
    if match is None:
        return None

    year_text = match.group("year")
    if year_text is None:
        year = datetime.now().year
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
    match = SCORE_RE.match(text.strip())
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


def _extract_first_link(row: Tag) -> str | None:
    link = row.find("a", href=True)
    return link["href"] if link is not None else None


def _league_url_from_round_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if not parts:
        return url
    return f"{parsed.scheme}://{parsed.netloc}/{parts[0]}/"
