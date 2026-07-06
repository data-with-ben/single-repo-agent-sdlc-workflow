from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Game, ObjectiveResult, Season, Team, User
from app.weekly_wrap import (
    biggest_market_swing,
    generate_weekly_wrap,
    star_performer,
    team_records,
)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
WEEK_START = NOW - timedelta(days=7)
WEEK_END = NOW


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'weekly_wrap_test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


_email_counter = iter(range(1_000_000))


def _make_user(db_session, roles=None) -> User:
    user = User(
        display_name=f"User {next(_email_counter)}",
        email=f"user{next(_email_counter)}@example.com",
        roles=roles or ["consultant"],
        created_at=datetime(2020, 1, 1),
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _make_season_and_teams(db_session):
    season = Season(
        name="S",
        start_date=WEEK_START - timedelta(days=30),
        end_date=WEEK_END + timedelta(days=30),
        status="active",
        team_size=3,
    )
    db_session.add(season)
    db_session.flush()
    home = Team(season_id=season.id, name="Home")
    away = Team(season_id=season.id, name="Away")
    db_session.add_all([home, away])
    db_session.commit()
    return season, home, away


def _make_game(db_session, season, home, away, game_date, home_score, away_score):
    game = Game(
        game_date=game_date,
        season_id=season.id,
        home_team_id=home.id,
        away_team_id=away.id,
        home_score=home_score,
        away_score=away_score,
        revealed=True,
        state="final",
    )
    db_session.add(game)
    db_session.commit()
    return game


class TestTeamRecords:
    def test_computes_wins_losses_and_draws(self, db_session):
        season, home, away = _make_season_and_teams(db_session)
        mid_week = WEEK_START + timedelta(days=1)
        _make_game(db_session, season, home, away, mid_week, 20.0, 10.0)
        _make_game(
            db_session, season, home, away, mid_week + timedelta(days=1), 10.0, 20.0
        )
        _make_game(
            db_session, season, home, away, mid_week + timedelta(days=2), 15.0, 15.0
        )

        records = {r.team_id: r for r in team_records(db_session, WEEK_START, WEEK_END)}

        assert records[home.id].wins == 1
        assert records[home.id].losses == 1
        assert records[home.id].draws == 1
        assert records[away.id].wins == 1
        assert records[away.id].losses == 1
        assert records[away.id].draws == 1

    def test_postponed_games_are_excluded_from_records(self, db_session):
        season, home, away = _make_season_and_teams(db_session)
        _make_game(
            db_session, season, home, away, WEEK_START + timedelta(days=1), None, None
        )

        records = {r.team_id: r for r in team_records(db_session, WEEK_START, WEEK_END)}

        assert records[home.id].wins == 0
        assert records[home.id].losses == 0
        assert records[home.id].draws == 0

    def test_games_outside_the_week_are_excluded(self, db_session):
        season, home, away = _make_season_and_teams(db_session)
        _make_game(
            db_session,
            season,
            home,
            away,
            WEEK_START - timedelta(days=1),
            20.0,
            10.0,
        )

        records = team_records(db_session, WEEK_START, WEEK_END)

        assert records == []


class TestBiggestMarketSwing:
    def test_picks_the_consultant_with_the_largest_absolute_swing(self, db_session):
        season, home, away = _make_season_and_teams(db_session)
        big_mover = _make_user(db_session)
        _make_user(db_session)  # a second, unaffected consultant

        game = _make_game(
            db_session, season, home, away, WEEK_START + timedelta(days=1), 10.0, 5.0
        )
        db_session.add(
            ObjectiveResult(
                game_id=game.id,
                game_date=WEEK_START + timedelta(days=1),
                consultant_id=big_mover.id,
                team_id=home.id,
                points=30,
            )
        )
        db_session.commit()

        swing = biggest_market_swing(db_session, WEEK_START, WEEK_END)

        assert swing is not None
        assert swing.consultant_id == big_mover.id
        assert swing.swing_pct > 0

    def test_no_consultants_returns_none(self, db_session):
        assert biggest_market_swing(db_session, WEEK_START, WEEK_END) is None

    def test_zero_starting_fair_value_is_skipped_without_dividing_by_zero(
        self, db_session
    ):
        from unittest.mock import patch

        from app.pricing import PriceQuote

        _make_user(db_session)
        zero_quote = PriceQuote(fair_value=0.0, buy_price=0.0, sell_price=0.0)
        with patch(
            "app.weekly_wrap.quote_for_consultant", return_value=zero_quote
        ):
            assert biggest_market_swing(db_session, WEEK_START, WEEK_END) is None


class TestStarPerformer:
    def test_picks_the_highest_total_points_in_the_window(self, db_session):
        season, home, away = _make_season_and_teams(db_session)
        star = _make_user(db_session)
        other = _make_user(db_session)
        game = _make_game(
            db_session, season, home, away, WEEK_START + timedelta(days=1), 10.0, 5.0
        )
        db_session.add_all(
            [
                ObjectiveResult(
                    game_id=game.id,
                    game_date=WEEK_START + timedelta(days=1),
                    consultant_id=star.id,
                    team_id=home.id,
                    points=30,
                ),
                ObjectiveResult(
                    game_id=game.id,
                    game_date=WEEK_START + timedelta(days=1),
                    consultant_id=other.id,
                    team_id=away.id,
                    points=10,
                ),
            ]
        )
        db_session.commit()

        performer = star_performer(db_session, WEEK_START, WEEK_END)

        assert performer is not None
        assert performer.consultant_id == star.id
        assert performer.total_points == 30

    def test_no_results_returns_none(self, db_session):
        assert star_performer(db_session, WEEK_START, WEEK_END) is None

    def test_ties_broken_by_lowest_consultant_id(self, db_session):
        season, home, away = _make_season_and_teams(db_session)
        first = _make_user(db_session)
        second = _make_user(db_session)
        game = _make_game(
            db_session, season, home, away, WEEK_START + timedelta(days=1), 10.0, 5.0
        )
        db_session.add_all(
            [
                ObjectiveResult(
                    game_id=game.id,
                    game_date=WEEK_START + timedelta(days=1),
                    consultant_id=second.id,
                    team_id=home.id,
                    points=20,
                ),
                ObjectiveResult(
                    game_id=game.id,
                    game_date=WEEK_START + timedelta(days=1),
                    consultant_id=first.id,
                    team_id=away.id,
                    points=20,
                ),
            ]
        )
        db_session.commit()

        performer = star_performer(db_session, WEEK_START, WEEK_END)

        assert performer.consultant_id == min(first.id, second.id)


class TestGenerateWeeklyWrap:
    def test_bundles_all_three_sections(self, db_session):
        season, home, away = _make_season_and_teams(db_session)
        _make_game(
            db_session, season, home, away, WEEK_START + timedelta(days=1), 20.0, 10.0
        )

        wrap = generate_weekly_wrap(db_session, WEEK_START, WEEK_END)

        assert len(wrap.team_records) == 2
        assert wrap.biggest_market_swing is None or wrap.biggest_market_swing
        assert wrap.star_performer is None
