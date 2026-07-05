from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.game_scheduling import schedule_season_games
from app.models import (
    Client,
    Dividend,
    Game,
    ObjectiveResult,
    Team,
    TeamMembership,
    TimeEntry,
    User,
    Wallet,
)
from app.reveal import reveal_game_date
from app.season import create_season
from app.seed import seed

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
GAME_DATE = (NOW - timedelta(days=1)).date()
GAME_DATETIME = datetime(GAME_DATE.year, GAME_DATE.month, GAME_DATE.day, 9, 0, 0)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'reveal_test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


_email_counter = iter(range(1_000_000))


def _make_client(db_session) -> Client:
    client = Client(
        name=f"Client {next(_email_counter)}", status="active", created_at=NOW
    )
    db_session.add(client)
    db_session.commit()
    return client


def _make_consultant(db_session, status="active") -> User:
    user = User(
        display_name=f"Consultant {next(_email_counter)}",
        email=f"consultant{next(_email_counter)}@example.com",
        roles=["consultant"],
        created_at=NOW,
        status=status,
    )
    db_session.add(user)
    db_session.commit()
    return user


def _setup_two_team_game(db_session, home_points, away_points):
    """4 consultants (2 per team), one game on GAME_DATE, with a TimeEntry
    for each consultant driving the given objective points.
    """
    client = _make_client(db_session)
    consultants = [_make_consultant(db_session) for _ in range(4)]
    for c in consultants:
        db_session.add(Wallet(user_id=c.id, balance=0.0))
    db_session.commit()

    season = create_season(
        db_session,
        name="S",
        start_date=GAME_DATETIME,
        end_date=GAME_DATETIME + timedelta(days=1),
        team_size=3,
    )
    db_session.flush()
    home_team = Team(season_id=season.id, name="Home")
    away_team = Team(season_id=season.id, name="Away")
    db_session.add_all([home_team, away_team])
    db_session.flush()
    for c in consultants[:2]:
        db_session.add(TeamMembership(team_id=home_team.id, user_id=c.id))
    for c in consultants[2:]:
        db_session.add(TeamMembership(team_id=away_team.id, user_id=c.id))
    db_session.commit()

    game = Game(
        game_date=GAME_DATETIME,
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        state="scheduled",
        revealed=False,
    )
    db_session.add(game)
    db_session.flush()

    # Points are driven via projected_by_11/logged_same_day/eod_update flags,
    # not directly settable -- use simple always-on-time-style timestamps for
    # "home" (full 10+10+5=25pts-ish via early project + same day log + late
    # description) and a single late-only entry for "away" (10pts logged
    # same day only) so home outscores away deterministically.
    for c in consultants[:2]:
        db_session.add(
            TimeEntry(
                consultant_id=c.id,
                work_date=GAME_DATETIME,
                client_id=client.id,
                planned_hours=8,
                actual_hours=8,
                description="A" * 25,
                state="updated",
                projected_at=GAME_DATETIME.replace(hour=9),
                logged_at=GAME_DATETIME.replace(hour=14),
                updated_at=GAME_DATETIME.replace(hour=16),
                first_submitted_at=GAME_DATETIME.replace(hour=9),
            )
        )
    for c in consultants[2:]:
        db_session.add(
            TimeEntry(
                consultant_id=c.id,
                work_date=GAME_DATETIME,
                client_id=client.id,
                planned_hours=8,
                actual_hours=8,
                description=None,
                state="logged",
                projected_at=None,
                logged_at=GAME_DATETIME.replace(hour=14),
                updated_at=None,
                first_submitted_at=GAME_DATETIME.replace(hour=14),
            )
        )
    db_session.commit()
    return consultants, home_team, away_team, game


class TestRevealWritesObjectiveResultsAndGameScores:
    def test_writes_objective_results_and_finalizes_the_game(self, db_session):
        consultants, home_team, away_team, game = _setup_two_team_game(
            db_session, home_points=25, away_points=10
        )

        summary = reveal_game_date(db_session, GAME_DATE)
        db_session.commit()

        assert summary.objective_results_written == 4
        stored = db_session.query(ObjectiveResult).all()
        assert len(stored) == 4

        refreshed_game = db_session.get(Game, game.id)
        assert refreshed_game.state == "final"
        assert refreshed_game.revealed is True
        assert refreshed_game.home_score is not None
        assert refreshed_game.home_score > refreshed_game.away_score


class TestRevealIdempotent:
    def test_running_twice_produces_identical_results(self, db_session):
        _setup_two_team_game(db_session, home_points=25, away_points=10)

        reveal_game_date(db_session, GAME_DATE)
        db_session.commit()
        first_results = {
            r.consultant_id: (r.points, r.projected_by_11, r.perfect_day)
            for r in db_session.query(ObjectiveResult).all()
        }
        first_game = db_session.query(Game).one()
        first_scores = (first_game.home_score, first_game.away_score)
        first_dividend_count = db_session.query(Dividend).count()

        reveal_game_date(db_session, GAME_DATE)
        db_session.commit()
        second_results = {
            r.consultant_id: (r.points, r.projected_by_11, r.perfect_day)
            for r in db_session.query(ObjectiveResult).all()
        }
        second_game = db_session.query(Game).one()
        second_scores = (second_game.home_score, second_game.away_score)
        second_dividend_count = db_session.query(Dividend).count()

        assert second_results == first_results
        assert second_scores == first_scores
        assert second_dividend_count == first_dividend_count

    def test_wallets_are_not_double_credited_on_rerun(self, db_session):
        consultants, *_ = _setup_two_team_game(
            db_session, home_points=25, away_points=10
        )

        reveal_game_date(db_session, GAME_DATE)
        db_session.commit()
        balances_after_first = {
            c.id: db_session.get(Wallet, c.id).balance for c in consultants
        }

        reveal_game_date(db_session, GAME_DATE)
        db_session.commit()
        balances_after_second = {
            c.id: db_session.get(Wallet, c.id).balance for c in consultants
        }

        assert balances_after_second == balances_after_first


class TestRevealRecoversFromFailure:
    def test_a_failure_partway_through_leaves_no_partial_writes(self, db_session):
        _setup_two_team_game(db_session, home_points=25, away_points=10)

        with patch(
            "app.reveal.credit_dividends", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError):
                reveal_game_date(db_session, GAME_DATE)

        assert db_session.query(ObjectiveResult).count() == 0
        game = db_session.query(Game).one()
        assert game.state == "scheduled"
        assert game.revealed is False
        assert db_session.query(Dividend).count() == 0


class TestRevealByeTeamHandling:
    def test_bye_team_consultant_produces_no_objective_result_row(self, db_session):
        # 3 consultants: 2 on a team with a real game, 1 alone on a bye team
        # (no Game row references it), all with a TimeEntry on GAME_DATE.
        client = _make_client(db_session)
        consultants = [_make_consultant(db_session) for _ in range(3)]
        for c in consultants:
            db_session.add(Wallet(user_id=c.id, balance=0.0))
        db_session.commit()

        season = create_season(
            db_session,
            name="S",
            start_date=GAME_DATETIME,
            end_date=GAME_DATETIME + timedelta(days=1),
            team_size=3,
        )
        db_session.flush()
        team_a = Team(season_id=season.id, name="A")
        team_b = Team(season_id=season.id, name="B")
        bye_team = Team(season_id=season.id, name="Bye")
        db_session.add_all([team_a, team_b, bye_team])
        db_session.flush()
        db_session.add(TeamMembership(team_id=team_a.id, user_id=consultants[0].id))
        db_session.add(TeamMembership(team_id=team_b.id, user_id=consultants[1].id))
        db_session.add(TeamMembership(team_id=bye_team.id, user_id=consultants[2].id))
        db_session.commit()

        game = Game(
            game_date=GAME_DATETIME,
            season_id=season.id,
            home_team_id=team_a.id,
            away_team_id=team_b.id,
            state="scheduled",
            revealed=False,
        )
        db_session.add(game)
        db_session.flush()

        for c in consultants:
            db_session.add(
                TimeEntry(
                    consultant_id=c.id,
                    work_date=GAME_DATETIME,
                    client_id=client.id,
                    planned_hours=8,
                    actual_hours=8,
                    description=None,
                    state="logged",
                    projected_at=None,
                    logged_at=GAME_DATETIME.replace(hour=14),
                    updated_at=None,
                    first_submitted_at=GAME_DATETIME.replace(hour=14),
                )
            )
        db_session.commit()

        summary = reveal_game_date(db_session, GAME_DATE)
        db_session.commit()

        assert summary.objective_results_written == 2
        stored_consultant_ids = {
            r.consultant_id for r in db_session.query(ObjectiveResult).all()
        }
        assert consultants[2].id not in stored_consultant_ids
        assert consultants[0].id in stored_consultant_ids


class TestRevealOverSeedData:
    def test_runs_end_to_end_without_error_over_real_seed_data(self, tmp_path):
        import app.seed as app_seed

        engine = create_engine(f"sqlite:///{tmp_path / 'seed_reveal_test.db'}")
        Base.metadata.create_all(engine)
        TestSessionLocal = sessionmaker(bind=engine)

        with patch.object(app_seed, "SessionLocal", TestSessionLocal):
            seed()

        session = TestSessionLocal()
        try:
            earliest_entry = (
                session.query(TimeEntry).order_by(TimeEntry.work_date.asc()).first()
            )
            target_date = earliest_entry.work_date.date()
            target_datetime = datetime(
                target_date.year, target_date.month, target_date.day
            )

            consultants = (
                session.query(User).filter(User.roles.isnot(None)).all()
            )
            consultant_ids = [
                u.id for u in consultants if "consultant" in u.roles
            ]

            test_season = create_season(
                session,
                name="Reveal Test Season",
                start_date=target_datetime,
                end_date=target_datetime + timedelta(days=1),
                team_size=4,
            )
            session.flush()
            for i in range(0, len(consultant_ids), 4):
                chunk = consultant_ids[i : i + 4]
                if len(chunk) < 3:
                    continue
                team = Team(season_id=test_season.id, name=f"RevealTeam{i}")
                session.add(team)
                session.flush()
                for uid in chunk:
                    session.add(TeamMembership(team_id=team.id, user_id=uid))
            session.commit()

            schedule_season_games(session, test_season)
            session.commit()

            summary = reveal_game_date(session, target_date)
            session.commit()

            assert summary.objective_results_written >= 1
            assert summary.games_finalized >= 1
            finalized_games = (
                session.query(Game)
                .filter(Game.season_id == test_season.id, Game.state == "final")
                .all()
            )
            assert len(finalized_games) >= 1
        finally:
            session.close()
