from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.game_scheduling import build_schedule, schedule_season_games
from app.models import Game, Team
from app.season import create_season

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'schedule_test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _weekday_range(start: datetime, count: int) -> list[datetime]:
    days = []
    cursor = start
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


# 2026-07-06 is a Monday.
MONDAY = datetime(2026, 7, 6)


class TestBuildScheduleTooFewTeams:
    def test_fewer_than_two_teams_raises(self):
        with pytest.raises(ValueError):
            build_schedule([1], _weekday_range(MONDAY, 5))

    def test_zero_teams_raises(self):
        with pytest.raises(ValueError):
            build_schedule([], _weekday_range(MONDAY, 5))


class TestNoDoubleBooking:
    @pytest.mark.parametrize("team_count", list(range(2, 13)))
    def test_no_team_appears_twice_on_the_same_date(self, team_count):
        team_ids = list(range(1, team_count + 1))
        workdays = _weekday_range(MONDAY, 20)

        games, _byes = build_schedule(team_ids, workdays)

        by_date: dict[datetime, list[int]] = {}
        for date, home, away in games:
            by_date.setdefault(date, []).extend([home, away])

        for date, appearances in by_date.items():
            assert len(appearances) == len(set(appearances)), (
                f"team double-booked on {date}"
            )


class TestBalancedSchedule:
    @pytest.mark.parametrize("team_count", list(range(2, 13)))
    def test_game_counts_are_balanced_across_a_full_cycle(self, team_count):
        team_ids = list(range(1, team_count + 1))
        # One full round-robin cycle: even -> N-1 rounds, odd -> N rounds.
        cycle_length = team_count if team_count % 2 else team_count - 1
        workdays = _weekday_range(MONDAY, cycle_length)

        games, byes = build_schedule(team_ids, workdays)

        game_counts = Counter()
        for _date, home, away in games:
            game_counts[home] += 1
            game_counts[away] += 1
        bye_counts = Counter(byes.values())

        for team_id in team_ids:
            total = game_counts[team_id] + bye_counts.get(team_id, 0)
            assert total == cycle_length

    def test_uneven_season_length_differs_by_at_most_one_game(self):
        team_ids = list(range(1, 6))  # 5 teams, odd -> byes needed
        workdays = _weekday_range(MONDAY, 17)  # not a multiple of the 5-round cycle

        games, byes = build_schedule(team_ids, workdays)

        game_counts = Counter()
        for _date, home, away in games:
            game_counts[home] += 1
            game_counts[away] += 1
        bye_counts = Counter(byes.values())

        totals = [game_counts[t] + bye_counts.get(t, 0) for t in team_ids]
        assert max(totals) - min(totals) <= 1


class TestByesRotate:
    def test_every_team_byes_exactly_once_per_cycle_when_odd(self):
        team_ids = [1, 2, 3, 4, 5]
        workdays = _weekday_range(MONDAY, 5)

        _games, byes = build_schedule(team_ids, workdays)

        bye_teams = list(byes.values())
        assert sorted(bye_teams) == team_ids

    def test_no_byes_when_team_count_is_even(self):
        team_ids = [1, 2, 3, 4]
        workdays = _weekday_range(MONDAY, 10)

        _games, byes = build_schedule(team_ids, workdays)

        assert byes == {}


class TestEveryTeamPlaysEveryOtherTeam:
    @pytest.mark.parametrize("team_count", [3, 4, 5, 6, 7, 8])
    def test_full_cycle_covers_every_pairing_exactly_once(self, team_count):
        team_ids = list(range(1, team_count + 1))
        cycle_length = team_count if team_count % 2 else team_count - 1
        workdays = _weekday_range(MONDAY, cycle_length)

        games, _byes = build_schedule(team_ids, workdays)

        pairs = {frozenset((home, away)) for _date, home, away in games}
        expected_pairs = {
            frozenset((a, b))
            for i, a in enumerate(team_ids)
            for b in team_ids[i + 1 :]
        }
        assert pairs == expected_pairs


class TestScheduleSeasonGames:
    def _make_season_with_teams(self, db_session, team_count, days=10):
        season = create_season(
            db_session,
            name="Season 1",
            start_date=MONDAY,
            end_date=MONDAY + timedelta(days=days),
            team_size=4,
        )
        db_session.flush()
        for i in range(team_count):
            db_session.add(Team(season_id=season.id, name=f"Team {i + 1}"))
        db_session.commit()
        return season

    def test_creates_game_rows_for_the_season(self, db_session):
        season = self._make_season_with_teams(db_session, 4)

        created, byes = schedule_season_games(db_session, season)
        db_session.commit()

        assert len(created) > 0
        assert byes == {}
        stored = db_session.query(Game).filter(Game.season_id == season.id).all()
        assert len(stored) == len(created)
        for game in stored:
            assert game.state == "scheduled"
            assert game.revealed is False
            assert game.home_score is None
            assert game.away_score is None

    def test_odd_team_count_surfaces_byes_without_a_game_row(self, db_session):
        season = self._make_season_with_teams(db_session, 5)

        created, byes = schedule_season_games(db_session, season)
        db_session.commit()

        assert len(byes) > 0
        team_ids = {
            t.id
            for t in db_session.query(Team).filter(Team.season_id == season.id).all()
        }
        assert set(byes.values()) <= team_ids
        for game in created:
            assert game.home_team_id != game.away_team_id

    def test_rerunning_schedule_replaces_rather_than_duplicates(self, db_session):
        season = self._make_season_with_teams(db_session, 6)

        schedule_season_games(db_session, season)
        db_session.commit()
        first_count = (
            db_session.query(Game).filter(Game.season_id == season.id).count()
        )

        schedule_season_games(db_session, season)
        db_session.commit()
        second_count = (
            db_session.query(Game).filter(Game.season_id == season.id).count()
        )

        assert second_count == first_count

    def test_too_few_teams_raises(self, db_session):
        season = self._make_season_with_teams(db_session, 1)

        with pytest.raises(ValueError):
            schedule_season_games(db_session, season)
