from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.dividends import (
    PERFECT_DAY_PER_SHARE,
    STAR_OF_GAME_PER_SHARE,
    TEAM_WIN_PER_SHARE,
    DividendAward,
    compute_dividend_awards,
    credit_dividends,
    dividend_feed,
)
from app.models import Dividend, User, Wallet
from app.objective_engine import ObjectiveResult
from app.team_scoring import GameResult
from app.trading import execute_buy, execute_sell

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
GAME_DATE = date(2026, 7, 6)
GAME_DATETIME = datetime(2026, 7, 6, 9, 0, 0)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dividends_test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


_email_counter = iter(range(1_000_000))


def _make_user(db_session) -> User:
    user = User(
        display_name=f"User {next(_email_counter)}",
        email=f"user{next(_email_counter)}@example.com",
        roles=["consultant"],
        created_at=NOW,
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _result(consultant_id, points=10, perfect_day=False) -> ObjectiveResult:
    return ObjectiveResult(
        consultant_id=consultant_id,
        game_date=GAME_DATE,
        projected_by_11=True,
        logged_same_day=True,
        eod_update=False,
        perfect_day=perfect_day,
        points=points,
    )


def _game(home_team, away_team, winner, is_draw=False, postponed=False) -> GameResult:
    return GameResult(
        game_id=1,
        home_team_id=home_team,
        away_team_id=away_team,
        home_score=10.0,
        away_score=5.0,
        home_bonus_applied=False,
        away_bonus_applied=False,
        winner_team_id=winner,
        is_draw=is_draw,
        postponed=postponed,
    )


class TestComputeDividendAwardsTeamWin:
    def test_every_present_winner_gets_a_team_win_award(self):
        results = [_result(1), _result(2), _result(3), _result(4)]
        team_memberships = {10: {1, 2}, 20: {3, 4}}
        games = [_game(home_team=10, away_team=20, winner=10)]

        awards = compute_dividend_awards(results, team_memberships, games)

        team_win_ids = {a.consultant_id for a in awards if a.reason == "team_win"}
        assert team_win_ids == {1, 2}
        assert all(
            a.per_share == TEAM_WIN_PER_SHARE
            for a in awards
            if a.reason == "team_win"
        )

    def test_losing_team_gets_no_team_win_award(self):
        results = [_result(1), _result(2), _result(3), _result(4)]
        team_memberships = {10: {1, 2}, 20: {3, 4}}
        games = [_game(home_team=10, away_team=20, winner=10)]

        awards = compute_dividend_awards(results, team_memberships, games)

        team_win_ids = {a.consultant_id for a in awards if a.reason == "team_win"}
        assert 3 not in team_win_ids
        assert 4 not in team_win_ids

    def test_draw_produces_no_team_win_award(self):
        results = [_result(1), _result(2)]
        team_memberships = {10: {1}, 20: {2}}
        games = [_game(home_team=10, away_team=20, winner=None, is_draw=True)]

        awards = compute_dividend_awards(results, team_memberships, games)

        assert not any(a.reason == "team_win" for a in awards)

    def test_postponed_game_produces_no_awards_at_all(self):
        results = [_result(1), _result(2)]
        team_memberships = {10: {1}, 20: {2}}
        games = [_game(home_team=10, away_team=20, winner=None, postponed=True)]

        awards = compute_dividend_awards(results, team_memberships, games)

        assert awards == []


class TestComputeDividendAwardsPerfectDay:
    def test_every_perfect_day_result_gets_an_award_regardless_of_game_outcome(self):
        results = [_result(1, perfect_day=True), _result(2, perfect_day=False)]
        team_memberships = {10: {1, 2}}
        games = []

        awards = compute_dividend_awards(results, team_memberships, games)

        perfect_day_ids = {a.consultant_id for a in awards if a.reason == "perfect_day"}
        assert perfect_day_ids == {1}
        assert all(
            a.per_share == PERFECT_DAY_PER_SHARE
            for a in awards
            if a.reason == "perfect_day"
        )


class TestComputeDividendAwardsStarOfGame:
    def test_top_scorer_on_losing_team_gets_the_award(self):
        results = [
            _result(1, points=10),
            _result(2, points=10),
            _result(3, points=25),
            _result(4, points=5),
        ]
        team_memberships = {10: {1, 2}, 20: {3, 4}}
        games = [_game(home_team=10, away_team=20, winner=10)]

        awards = compute_dividend_awards(results, team_memberships, games)

        star_awards = [a for a in awards if a.reason == "star_of_game"]
        assert len(star_awards) == 1
        assert star_awards[0].consultant_id == 3
        assert star_awards[0].per_share == STAR_OF_GAME_PER_SHARE

    def test_ties_broken_by_lowest_consultant_id(self):
        results = [
            _result(1, points=10),
            _result(2, points=10),
            _result(5, points=25),
        ]
        team_memberships = {10: {5}, 20: {1, 2}}
        games = [_game(home_team=10, away_team=20, winner=10)]

        awards = compute_dividend_awards(results, team_memberships, games)

        star_awards = [a for a in awards if a.reason == "star_of_game"]
        assert star_awards[0].consultant_id == 1

    def test_draw_produces_no_star_of_game_award(self):
        results = [_result(1), _result(2)]
        team_memberships = {10: {1}, 20: {2}}
        games = [_game(home_team=10, away_team=20, winner=None, is_draw=True)]

        awards = compute_dividend_awards(results, team_memberships, games)

        assert not any(a.reason == "star_of_game" for a in awards)

    def test_no_present_losers_produces_no_star_of_game_award(self):
        # Defensive edge case: a winner with no present roster on the
        # losing side (team_scoring.resolve_games would normally postpone
        # such a game, but compute_dividend_awards accepts game_results as
        # a plain input and should not crash on this shape).
        results = [_result(1)]
        team_memberships = {10: {1}, 20: set()}
        games = [_game(home_team=10, away_team=20, winner=10)]

        awards = compute_dividend_awards(results, team_memberships, games)

        assert not any(a.reason == "star_of_game" for a in awards)


class TestCreditDividendsPaysShareholders:
    def test_shareholder_is_credited_the_correct_total(self, db_session):
        shareholder = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(Wallet(user_id=shareholder.id, balance=100000.0))
        db_session.commit()
        execute_buy(
            db_session, shareholder.id, consultant.id, shares=10, now=GAME_DATETIME
        )
        db_session.commit()
        balance_after_buy = db_session.get(Wallet, shareholder.id).balance

        awards = [DividendAward(consultant.id, "team_win", TEAM_WIN_PER_SHARE)]
        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()

        wallet = db_session.get(Wallet, shareholder.id)
        assert wallet.balance == pytest.approx(
            balance_after_buy + 10 * TEAM_WIN_PER_SHARE
        )
        dividend = db_session.query(Dividend).one()
        assert dividend.user_id == shareholder.id
        assert dividend.consultant_id == consultant.id
        assert dividend.reason == "team_win"
        assert dividend.shares == 10
        assert dividend.per_share == TEAM_WIN_PER_SHARE
        assert dividend.total == pytest.approx(10 * TEAM_WIN_PER_SHARE)

    def test_multiple_shareholders_are_each_paid_per_their_own_shares(self, db_session):
        alice = _make_user(db_session)
        bob = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(Wallet(user_id=alice.id, balance=100000.0))
        db_session.add(Wallet(user_id=bob.id, balance=100000.0))
        db_session.commit()
        execute_buy(db_session, alice.id, consultant.id, shares=10, now=GAME_DATETIME)
        execute_buy(db_session, bob.id, consultant.id, shares=3, now=GAME_DATETIME)
        db_session.commit()

        awards = [DividendAward(consultant.id, "perfect_day", PERFECT_DAY_PER_SHARE)]
        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()

        dividends = {
            d.user_id: d for d in db_session.query(Dividend).all()
        }
        assert dividends[alice.id].shares == 10
        assert dividends[bob.id].shares == 3

    def test_self_holding_consultant_is_paid_like_any_other_shareholder(
        self, db_session
    ):
        consultant = _make_user(db_session)
        db_session.add(Wallet(user_id=consultant.id, balance=100000.0))
        db_session.commit()
        execute_buy(
            db_session, consultant.id, consultant.id, shares=5, now=GAME_DATETIME
        )
        db_session.commit()
        balance_after_buy = db_session.get(Wallet, consultant.id).balance

        awards = [DividendAward(consultant.id, "team_win", TEAM_WIN_PER_SHARE)]
        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()

        wallet = db_session.get(Wallet, consultant.id)
        assert wallet.balance == pytest.approx(
            balance_after_buy + 5 * TEAM_WIN_PER_SHARE
        )


class TestCreditDividendsZeroShares:
    def test_a_holder_who_sold_all_shares_before_the_game_date_receives_nothing(
        self, db_session
    ):
        shareholder = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(Wallet(user_id=shareholder.id, balance=100000.0))
        db_session.commit()
        execute_buy(
            db_session,
            shareholder.id,
            consultant.id,
            shares=10,
            now=GAME_DATETIME - timedelta(days=2),
        )
        db_session.commit()
        execute_sell(
            db_session,
            shareholder.id,
            consultant.id,
            shares=10,
            now=GAME_DATETIME - timedelta(days=1),
        )
        db_session.commit()
        balance_before_dividends = db_session.get(Wallet, shareholder.id).balance

        awards = [DividendAward(consultant.id, "team_win", TEAM_WIN_PER_SHARE)]
        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()

        wallet = db_session.get(Wallet, shareholder.id)
        assert wallet.balance == balance_before_dividends
        assert db_session.query(Dividend).count() == 0

    def test_a_consultant_with_no_shareholders_at_all_produces_no_dividends(
        self, db_session
    ):
        consultant = _make_user(db_session)

        awards = [DividendAward(consultant.id, "team_win", TEAM_WIN_PER_SHARE)]
        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()

        assert db_session.query(Dividend).count() == 0


class TestCreditDividendsIdempotent:
    def test_running_twice_does_not_double_pay(self, db_session):
        shareholder = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(Wallet(user_id=shareholder.id, balance=100000.0))
        db_session.commit()
        execute_buy(
            db_session, shareholder.id, consultant.id, shares=10, now=GAME_DATETIME
        )
        db_session.commit()

        awards = [DividendAward(consultant.id, "team_win", TEAM_WIN_PER_SHARE)]
        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()
        balance_after_first_run = db_session.get(Wallet, shareholder.id).balance

        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()

        wallet = db_session.get(Wallet, shareholder.id)
        assert wallet.balance == balance_after_first_run
        assert db_session.query(Dividend).count() == 1


class TestCreditDividendsCreatesWalletIfMissing:
    def test_shareholder_with_no_existing_wallet_row_gets_one_created(
        self, db_session
    ):
        shareholder = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(Wallet(user_id=shareholder.id, balance=100000.0))
        db_session.commit()
        execute_buy(
            db_session, shareholder.id, consultant.id, shares=4, now=GAME_DATETIME
        )
        db_session.commit()
        # Remove the wallet row entirely to force credit_dividends to
        # re-create it, mirroring trading.py's own get-or-create test.
        db_session.query(Wallet).filter(Wallet.user_id == shareholder.id).delete()
        db_session.commit()

        awards = [DividendAward(consultant.id, "team_win", TEAM_WIN_PER_SHARE)]
        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()

        wallet = db_session.get(Wallet, shareholder.id)
        assert wallet is not None
        assert wallet.balance == pytest.approx(4 * TEAM_WIN_PER_SHARE)


class TestPointInTimeShareholding:
    def test_shares_bought_after_the_game_date_do_not_inflate_the_payout(
        self, db_session
    ):
        shareholder = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(Wallet(user_id=shareholder.id, balance=100000.0))
        db_session.commit()
        execute_buy(
            db_session, shareholder.id, consultant.id, shares=5, now=GAME_DATETIME
        )
        db_session.commit()
        # Buys more shares the day after the game date, before dividends run.
        execute_buy(
            db_session,
            shareholder.id,
            consultant.id,
            shares=20,
            now=GAME_DATETIME + timedelta(days=1),
        )
        db_session.commit()

        awards = [DividendAward(consultant.id, "team_win", TEAM_WIN_PER_SHARE)]
        credit_dividends(db_session, GAME_DATE, awards)
        db_session.commit()

        dividend = db_session.query(Dividend).one()
        assert dividend.shares == 5


class TestDividendFeed:
    def test_returns_rows_ordered_by_game_date_descending(self, db_session):
        shareholder = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(Wallet(user_id=shareholder.id, balance=100000.0))
        db_session.commit()
        execute_buy(
            db_session,
            shareholder.id,
            consultant.id,
            shares=10,
            now=GAME_DATETIME - timedelta(days=10),
        )
        db_session.commit()

        credit_dividends(
            db_session,
            GAME_DATE - timedelta(days=1),
            [DividendAward(consultant.id, "perfect_day", PERFECT_DAY_PER_SHARE)],
        )
        db_session.commit()
        credit_dividends(
            db_session,
            GAME_DATE,
            [DividendAward(consultant.id, "team_win", TEAM_WIN_PER_SHARE)],
        )
        db_session.commit()

        feed = dividend_feed(db_session, shareholder.id)

        assert len(feed) == 2
        assert feed[0].reason == "team_win"
        assert feed[1].reason == "perfect_day"
        assert all(row.user_id == shareholder.id for row in feed)
