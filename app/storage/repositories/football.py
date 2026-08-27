from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.parser.dto import LeaguePageData, ParsedMatch, ParsedRound, ParsedStandingRow
from app.services.subscriptions.dto import CurrentRoundView, LeagueView, StandingTableView, TelegramUserProfile
from app.services.updates.sync import ParserRunDraft, SaveLeaguePageResult
from app.storage.models import (
    DataChangeEvent,
    League,
    Match,
    ParserRun,
    Round,
    Season,
    StandingRow,
    StandingSnapshot,
    Subscription,
    Team,
    User,
)


@dataclass(frozen=True)
class MatchUpsertResult:
    match: Match
    created: bool
    changed: bool
    finished_now: bool


class FootballDataSqlAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_league_page_data(self, data: LeaguePageData) -> SaveLeaguePageResult:
        league = await self._upsert_league(data)
        season = await self._upsert_season(league, data)

        created_matches = 0
        updated_matches = 0
        created_change_events = 0

        for parsed_round in _iter_league_rounds(data):
            round_ = await self._upsert_round(
                league,
                season,
                parsed_round,
                is_current=data.current_round is not None and parsed_round.number == data.current_round.number,
            )
            for parsed_match in parsed_round.matches:
                result = await self._upsert_match(league, season, round_, parsed_match)
                if result.created:
                    created_matches += 1
                    await self._add_change_event("match_created", league=league, match=result.match)
                    created_change_events += 1
                elif result.changed:
                    updated_matches += 1
                    event_type = "match_finished" if result.finished_now else "match_updated"
                    await self._add_change_event(event_type, league=league, match=result.match)
                    created_change_events += 1

        if data.standings:
            await self._replace_standings_snapshot(league, season, data.standings, source_url=data.league.source_url)

        await self._session.flush()
        return SaveLeaguePageResult(
            created_matches=created_matches,
            updated_matches=updated_matches,
            created_change_events=created_change_events,
        )

    async def record_parser_run(self, run: ParserRunDraft) -> None:
        self._session.add(
            ParserRun(
                source=run.source,
                target_type=run.target_type,
                target_url=run.target_url,
                status=run.status,
                started_at=run.started_at,
                finished_at=run.finished_at,
                http_status=run.http_status,
                error_message=run.error_message,
            )
        )
        await self._session.flush()

    async def upsert_telegram_user(self, profile: TelegramUserProfile) -> None:
        statement = select(User).where(User.telegram_user_id == profile.telegram_user_id)
        user = await self._session.scalar(statement)

        if user is None:
            self._session.add(
                User(
                    telegram_user_id=profile.telegram_user_id,
                    username=profile.username,
                    display_name=profile.display_name,
                    language_code=profile.language_code,
                )
            )
        else:
            user.username = profile.username
            user.display_name = profile.display_name
            user.language_code = profile.language_code

        await self._session.flush()

    async def list_user_subscriptions(self, telegram_user_id: int) -> tuple[LeagueView, ...]:
        statement = (
            select(League.code, League.name)
            .join(Subscription, Subscription.league_id == League.id)
            .join(User, User.id == Subscription.user_id)
            .where(User.telegram_user_id == telegram_user_id, Subscription.is_active.is_(True))
            .order_by(League.name)
        )
        result = await self._session.execute(statement)
        return tuple(LeagueView(code=row.code, name=row.name) for row in result)

    async def list_user_subscription_codes(self, telegram_user_id: int) -> frozenset[str]:
        subscriptions = await self.list_user_subscriptions(telegram_user_id)
        return frozenset(league.code for league in subscriptions)

    async def toggle_league_subscription(self, *, telegram_user_id: int, league_code: str) -> tuple[LeagueView, bool]:
        user = await self._get_user_by_telegram_id(telegram_user_id)
        league = await self._get_active_league_by_code(league_code)
        if user is None or league is None:
            raise ValueError(f"Unknown user or league: {telegram_user_id}, {league_code}")

        statement = select(Subscription).where(Subscription.user_id == user.id, Subscription.league_id == league.id)
        subscription = await self._session.scalar(statement)

        if subscription is None:
            subscription = Subscription(user_id=user.id, league_id=league.id, is_active=True)
            self._session.add(subscription)
            is_active = True
        else:
            subscription.is_active = not subscription.is_active
            is_active = subscription.is_active

        await self._session.flush()
        return LeagueView(code=league.code, name=league.name), is_active

    async def get_current_round(self, league_code: str) -> CurrentRoundView | None:
        league = await self._get_active_league_by_code(league_code)
        if league is None:
            return None

        statement = (
            select(Round)
            .join(Season, Season.id == Round.season_id)
            .where(Round.league_id == league.id, Season.is_current.is_(True), Round.status == "active")
            .order_by(desc(Round.round_number))
            .limit(1)
        )
        round_ = await self._session.scalar(statement)
        if round_ is None:
            return CurrentRoundView(league=LeagueView(code=league.code, name=league.name), round=None)

        return CurrentRoundView(
            league=LeagueView(code=league.code, name=league.name),
            round=ParsedRound(
                number=round_.round_number,
                source_url=round_.source_url,
                matches=await self._load_round_matches(round_),
            ),
        )

    async def get_latest_standings(self, league_code: str) -> StandingTableView | None:
        league = await self._get_active_league_by_code(league_code)
        if league is None:
            return None

        statement = (
            select(StandingSnapshot)
            .join(Season, Season.id == StandingSnapshot.season_id)
            .where(
                StandingSnapshot.league_id == league.id,
                Season.is_current.is_(True),
            )
            .order_by(desc(StandingSnapshot.collected_at))
            .limit(1)
        )
        snapshot = await self._session.scalar(statement)
        if snapshot is None:
            return StandingTableView(league=LeagueView(code=league.code, name=league.name), rows=())

        rows = await self._load_standing_rows(snapshot)
        return StandingTableView(league=LeagueView(code=league.code, name=league.name), rows=rows)

    async def _upsert_league(self, data: LeaguePageData) -> League:
        statement = select(League).where(League.source == "kulichki", League.code == data.league.code)
        league = await self._session.scalar(statement)

        if league is None:
            league = League(
                source="kulichki",
                code=data.league.code,
                name=data.league.name,
                source_url=data.league.source_url,
                is_active=True,
            )
            self._session.add(league)
        else:
            league.name = data.league.name
            league.source_url = data.league.source_url

        await self._session.flush()
        return league

    async def _upsert_season(self, league: League, data: LeaguePageData) -> Season:
        source_season_key = data.source_season_key or "unknown"
        season_label = data.season_label or source_season_key
        statement = select(Season).where(
            Season.league_id == league.id,
            Season.source_season_key == source_season_key,
        )
        season = await self._session.scalar(statement)

        if season is None:
            season = Season(
                league_id=league.id,
                label=season_label,
                source_season_key=source_season_key,
                is_current=True,
            )
            self._session.add(season)
        else:
            season.label = season_label
            season.is_current = True

        await self._session.flush()
        return season

    async def _upsert_round(self, league: League, season: Season, parsed_round: ParsedRound, *, is_current: bool) -> Round:
        statement = select(Round).where(
            Round.season_id == season.id,
            Round.round_number == parsed_round.number,
        )
        round_ = await self._session.scalar(statement)

        if round_ is None:
            round_ = Round(
                league_id=league.id,
                season_id=season.id,
                round_number=parsed_round.number,
                source_url=parsed_round.source_url,
                status="active" if is_current else "planned",
            )
            self._session.add(round_)
        else:
            round_.league_id = league.id
            round_.source_url = parsed_round.source_url
            if is_current:
                round_.status = "active"

        await self._session.flush()
        return round_

    async def _upsert_match(
        self,
        league: League,
        season: Season,
        round_: Round,
        parsed_match: ParsedMatch,
    ) -> MatchUpsertResult:
        home_team = await self._upsert_team(parsed_match.home_team)
        away_team = await self._upsert_team(parsed_match.away_team)

        statement = select(Match).where(
            Match.source == "kulichki",
            Match.league_id == league.id,
            Match.season_id == season.id,
            Match.round_id == round_.id,
            Match.home_team_id == home_team.id,
            Match.away_team_id == away_team.id,
        )
        match = await self._session.scalar(statement)

        if match is None:
            match = Match(
                source="kulichki",
                source_url=parsed_match.source_url,
                league_id=league.id,
                season_id=season.id,
                round_id=round_.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                scheduled_at=parsed_match.scheduled_at,
                home_score=parsed_match.home_score,
                away_score=parsed_match.away_score,
                status=parsed_match.status,
                raw_status=parsed_match.status,
            )
            self._session.add(match)
            await self._session.flush()
            return MatchUpsertResult(match=match, created=True, changed=False, finished_now=False)

        old_state = (match.scheduled_at, match.home_score, match.away_score, match.status, match.source_url)
        old_status = match.status

        match.source_url = parsed_match.source_url
        match.scheduled_at = parsed_match.scheduled_at
        match.home_score = parsed_match.home_score
        match.away_score = parsed_match.away_score
        match.status = parsed_match.status
        match.raw_status = parsed_match.status

        new_state = (match.scheduled_at, match.home_score, match.away_score, match.status, match.source_url)
        changed = old_state != new_state
        finished_now = old_status != "finished" and match.status == "finished"

        await self._session.flush()
        return MatchUpsertResult(match=match, created=False, changed=changed, finished_now=finished_now)

    async def _upsert_team(self, source_name: str) -> Team:
        normalized_name = normalize_team_name(source_name)
        statement = select(Team).where(Team.source == "kulichki", Team.normalized_name == normalized_name)
        team = await self._session.scalar(statement)

        if team is None:
            team = Team(
                source="kulichki",
                source_name=source_name,
                normalized_name=normalized_name,
                display_name=source_name,
            )
            self._session.add(team)
        else:
            team.source_name = source_name
            team.display_name = source_name

        await self._session.flush()
        return team

    async def _replace_standings_snapshot(
        self,
        league: League,
        season: Season,
        standings: tuple[ParsedStandingRow, ...],
        *,
        source_url: str,
    ) -> StandingSnapshot:
        snapshot = StandingSnapshot(
            league_id=league.id,
            season_id=season.id,
            source_url=source_url,
        )
        self._session.add(snapshot)
        await self._session.flush()

        for row in standings:
            team = await self._upsert_team(row.team_name)
            self._session.add(
                StandingRow(
                    snapshot_id=snapshot.id,
                    team_id=team.id,
                    position=row.position,
                    played=row.played,
                    wins=None,
                    draws=None,
                    losses=None,
                    goals_for=None,
                    goals_against=None,
                    goal_difference=None,
                    points=row.points,
                    raw_values={},
                )
            )

        await self._session.flush()
        return snapshot

    async def _add_change_event(self, event_type: str, *, league: League, match: Match) -> None:
        self._session.add(
            DataChangeEvent(
                event_type=event_type,
                league_id=league.id,
                match_id=match.id,
                payload={},
            )
        )

    async def _get_user_by_telegram_id(self, telegram_user_id: int) -> User | None:
        return await self._session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))

    async def _get_active_league_by_code(self, league_code: str) -> League | None:
        return await self._session.scalar(
            select(League).where(League.source == "kulichki", League.code == league_code, League.is_active.is_(True))
        )

    async def _load_round_matches(self, round_: Round) -> tuple[ParsedMatch, ...]:
        HomeTeam = aliased(Team)
        AwayTeam = aliased(Team)
        statement = (
            select(Match, HomeTeam.display_name.label("home_name"), AwayTeam.display_name.label("away_name"))
            .join(HomeTeam, Match.home_team_id == HomeTeam.id)
            .join(AwayTeam, Match.away_team_id == AwayTeam.id)
            .where(Match.round_id == round_.id)
            .order_by(Match.scheduled_at, Match.id)
        )
        result = await self._session.execute(statement)

        return tuple(
            ParsedMatch(
                home_team=row.home_name,
                away_team=row.away_name,
                scheduled_at=row.Match.scheduled_at,
                home_score=row.Match.home_score,
                away_score=row.Match.away_score,
                status=row.Match.status,
                source_url=row.Match.source_url,
            )
            for row in result
        )

    async def _load_standing_rows(self, snapshot: StandingSnapshot) -> tuple[ParsedStandingRow, ...]:
        statement = (
            select(StandingRow, Team.display_name.label("team_name"))
            .join(Team, StandingRow.team_id == Team.id)
            .where(StandingRow.snapshot_id == snapshot.id)
            .order_by(StandingRow.position)
        )
        result = await self._session.execute(statement)

        return tuple(
            ParsedStandingRow(
                position=row.StandingRow.position,
                team_name=row.team_name,
                played=row.StandingRow.played,
                points=row.StandingRow.points,
            )
            for row in result
        )


def normalize_team_name(source_name: str) -> str:
    return re.sub(r"\s+", " ", source_name.strip().casefold())


def _iter_league_rounds(data: LeaguePageData) -> tuple[ParsedRound, ...]:
    if data.rounds:
        return data.rounds
    if data.current_round is not None:
        return (data.current_round,)
    return ()
