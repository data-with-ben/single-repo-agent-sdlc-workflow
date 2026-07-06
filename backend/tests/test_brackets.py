from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.brackets import (
    portfolio_gain,
    portfolio_value_at,
    resolve_matchup,
    weekly_brackets,
    weekly_pairings,
)
from app.db import Base
from app.models import Dividend, Holding, Transaction, User, Wallet

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
WEEK_START = NOW - timedelta(days=7)
WEEK_END = NOW


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'brackets_test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


_email_counter = iter(range(1_000_000))


def _make_user(db_session, created_at=None) -> User:
    user = User(
        display_name=f"User {next(_email_counter)}",
        email=f"user{next(_email_counter)}@example.com",
        roles=["consultant"],
        created_at=created_at or datetime(2020, 1, 1),
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _make_wallet(db_session, user_id, balance) -> Wallet:
    wallet = Wallet(user_id=user_id, balance=balance)
    db_session.add(wallet)
    db_session.commit()
    return wallet


class TestPortfolioValueAt:
    def test_wallet_only_when_no_holdings(self, db_session):
        user = _make_user(db_session)
        _make_wallet(db_session, user.id, 1000.0)

        assert portfolio_value_at(db_session, user.id, NOW) == 1000.0

    def test_reverse_replay_undoes_a_buy_after_the_cutoff(self, db_session):
        user = _make_user(db_session)
        consultant = _make_user(db_session)
        _make_wallet(db_session, user.id, 900.0)  # already debited by the buy below
        db_session.add(Holding(user_id=user.id, consultant_id=consultant.id, shares=5))
        db_session.add(
            Transaction(
                user_id=user.id,
                consultant_id=consultant.id,
                side="buy",
                shares=5,
                price_per_share=20.0,
                total=100.0,
                executed_at=WEEK_START + timedelta(days=1),
            )
        )
        db_session.commit()

        # Before the buy: no shares, balance not yet debited.
        value_before = portfolio_value_at(db_session, user.id, WEEK_START)

        assert value_before == 1000.0

    def test_reverse_replay_undoes_a_sell_after_the_cutoff(self, db_session):
        user = _make_user(db_session)
        consultant = _make_user(db_session)
        _make_wallet(db_session, user.id, 1100.0)  # already credited by the sell below
        db_session.add(Holding(user_id=user.id, consultant_id=consultant.id, shares=0))
        db_session.add(
            Transaction(
                user_id=user.id,
                consultant_id=consultant.id,
                side="sell",
                shares=5,
                price_per_share=20.0,
                total=100.0,
                executed_at=WEEK_START + timedelta(days=1),
            )
        )
        db_session.commit()

        # Before the sell: still held 5 shares, balance not yet credited.
        # quote_for_consultant on an empty history returns the BASE fair value.
        from app.trading import quote_for_consultant

        base_quote = quote_for_consultant(db_session, consultant.id, WEEK_START)
        value_before = portfolio_value_at(db_session, user.id, WEEK_START)

        assert value_before == 1000.0 + 5 * base_quote.fair_value

    def test_a_dividend_after_the_cutoff_is_undone(self, db_session):
        user = _make_user(db_session)
        consultant = _make_user(db_session)
        _make_wallet(db_session, user.id, 1050.0)  # already credited by the dividend
        db_session.add(
            Dividend(
                user_id=user.id,
                consultant_id=consultant.id,
                game_date=WEEK_START + timedelta(days=1),
                reason="team_win",
                shares=5,
                per_share=10.0,
                total=50.0,
            )
        )
        db_session.commit()

        value_before = portfolio_value_at(db_session, user.id, WEEK_START)

        assert value_before == 1000.0

    def test_fully_liquidated_stake_still_counted_at_an_earlier_cutoff(
        self, db_session
    ):
        user = _make_user(db_session)
        consultant = _make_user(db_session)
        _make_wallet(db_session, user.id, 1100.0)
        # Current state: 0 shares held (bought then fully sold after the cutoff).
        db_session.add(Holding(user_id=user.id, consultant_id=consultant.id, shares=0))
        db_session.add_all(
            [
                Transaction(
                    user_id=user.id,
                    consultant_id=consultant.id,
                    side="buy",
                    shares=5,
                    price_per_share=20.0,
                    total=100.0,
                    executed_at=WEEK_START + timedelta(days=1),
                ),
                Transaction(
                    user_id=user.id,
                    consultant_id=consultant.id,
                    side="sell",
                    shares=5,
                    price_per_share=20.0,
                    total=100.0,
                    executed_at=WEEK_START + timedelta(days=2),
                ),
            ]
        )
        db_session.commit()

        from app.trading import quote_for_consultant

        base_quote = quote_for_consultant(db_session, consultant.id, WEEK_START)
        value_before = portfolio_value_at(db_session, user.id, WEEK_START)

        # Before either transaction: 0 shares (buy hadn't happened yet), balance
        # untouched by either the buy debit or the sell credit.
        assert value_before == 1100.0 - 100.0 + 100.0
        assert value_before == 1100.0
        # The held stake existed strictly between the two transactions, not at
        # WEEK_START itself in this scenario -- confirm at that midpoint instead.
        midpoint = WEEK_START + timedelta(days=1, hours=12)
        value_midpoint = portfolio_value_at(db_session, user.id, midpoint)
        assert value_midpoint == 1000.0 + 5 * base_quote.fair_value


class TestPortfolioGain:
    def test_gain_is_the_difference_between_end_and_start_value(self, db_session):
        user = _make_user(db_session)
        consultant = _make_user(db_session)
        _make_wallet(db_session, user.id, 900.0)
        db_session.add(Holding(user_id=user.id, consultant_id=consultant.id, shares=5))
        db_session.add(
            Transaction(
                user_id=user.id,
                consultant_id=consultant.id,
                side="buy",
                shares=5,
                price_per_share=20.0,
                total=100.0,
                executed_at=WEEK_START + timedelta(days=1),
            )
        )
        db_session.commit()

        gain = portfolio_gain(db_session, user.id, WEEK_START, WEEK_END)

        # Started with 1000 (no holding yet), ends with wallet 900 + 5 shares
        # at their current fair value.
        end_value = portfolio_value_at(db_session, user.id, WEEK_END)
        assert gain == end_value - 1000.0


class TestWeeklyPairings:
    def test_pairs_every_wallet_holder(self, db_session):
        users = [_make_user(db_session) for _ in range(4)]
        for u in users:
            _make_wallet(db_session, u.id, 1000.0)

        matchups, bye_user_id = weekly_pairings(db_session, WEEK_START)

        assert bye_user_id is None
        paired_ids = {m.user_a_id for m in matchups} | {m.user_b_id for m in matchups}
        assert paired_ids == {u.id for u in users}
        assert len(matchups) == 2

    def test_odd_pool_leaves_one_user_with_a_bye(self, db_session):
        users = [_make_user(db_session) for _ in range(3)]
        for u in users:
            _make_wallet(db_session, u.id, 1000.0)

        matchups, bye_user_id = weekly_pairings(db_session, WEEK_START)

        assert bye_user_id is not None
        assert bye_user_id in {u.id for u in users}
        assert len(matchups) == 1

    def test_pairing_is_deterministic_for_the_same_week(self, db_session):
        users = [_make_user(db_session) for _ in range(6)]
        for u in users:
            _make_wallet(db_session, u.id, 1000.0)

        first_matchups, first_bye = weekly_pairings(db_session, WEEK_START)
        second_matchups, second_bye = weekly_pairings(db_session, WEEK_START)

        first_pairs = {frozenset((m.user_a_id, m.user_b_id)) for m in first_matchups}
        second_pairs = {frozenset((m.user_a_id, m.user_b_id)) for m in second_matchups}
        assert first_pairs == second_pairs
        assert first_bye == second_bye

    def test_wallet_holder_hired_after_the_week_start_is_excluded(self, db_session):
        existing = [_make_user(db_session) for _ in range(2)]
        for u in existing:
            _make_wallet(db_session, u.id, 1000.0)
        late_hire = _make_user(db_session, created_at=WEEK_END + timedelta(days=1))
        _make_wallet(db_session, late_hire.id, 1000.0)

        matchups, bye_user_id = weekly_pairings(db_session, WEEK_START)

        paired_ids = {m.user_a_id for m in matchups} | {m.user_b_id for m in matchups}
        pool = paired_ids | ({bye_user_id} if bye_user_id else set())
        assert late_hire.id not in pool


class TestResolveMatchup:
    def test_higher_gain_side_wins(self, db_session):
        from app.brackets import Matchup

        winner = _make_user(db_session)
        loser = _make_user(db_session)
        consultant = _make_user(db_session)
        _make_wallet(db_session, winner.id, 1200.0)  # credited by the dividend below
        _make_wallet(db_session, loser.id, 1000.0)
        db_session.add(
            Dividend(
                user_id=winner.id,
                consultant_id=consultant.id,
                game_date=WEEK_START + timedelta(days=1),
                reason="team_win",
                shares=5,
                per_share=40.0,
                total=200.0,
            )
        )
        db_session.commit()

        result = resolve_matchup(
            db_session, Matchup(winner.id, loser.id), WEEK_START, WEEK_END
        )

        assert result.winner_id == winner.id

    def test_equal_gain_is_a_draw(self, db_session):
        from app.brackets import Matchup

        a = _make_user(db_session)
        b = _make_user(db_session)
        _make_wallet(db_session, a.id, 1000.0)
        _make_wallet(db_session, b.id, 1000.0)

        result = resolve_matchup(db_session, Matchup(a.id, b.id), WEEK_START, WEEK_END)

        assert result.winner_id is None


class TestWeeklyBrackets:
    def test_bundles_pairings_and_results(self, db_session):
        users = [_make_user(db_session) for _ in range(4)]
        for u in users:
            _make_wallet(db_session, u.id, 1000.0)

        results, bye_user_id = weekly_brackets(db_session, WEEK_START, WEEK_END)

        assert bye_user_id is None
        assert len(results) == 2
        for r in results:
            assert r.winner_id is None  # no trades this week -> all draws


class TestNoMarketMutation:
    def test_brackets_functions_never_write_to_the_database(self, db_session):
        user = _make_user(db_session)
        consultant = _make_user(db_session)
        _make_wallet(db_session, user.id, 1000.0)
        db_session.add(Holding(user_id=user.id, consultant_id=consultant.id, shares=5))
        db_session.add(
            Transaction(
                user_id=user.id,
                consultant_id=consultant.id,
                side="buy",
                shares=5,
                price_per_share=20.0,
                total=100.0,
                executed_at=WEEK_START + timedelta(days=1),
            )
        )
        db_session.commit()

        wallet_before = db_session.get(Wallet, user.id).balance
        holding_before = (
            db_session.query(Holding)
            .filter(Holding.user_id == user.id, Holding.consultant_id == consultant.id)
            .first()
            .shares
        )
        txn_count_before = db_session.query(Transaction).count()

        weekly_brackets(db_session, WEEK_START, WEEK_END)

        assert db_session.get(Wallet, user.id).balance == wallet_before
        holding_after = (
            db_session.query(Holding)
            .filter(Holding.user_id == user.id, Holding.consultant_id == consultant.id)
            .first()
            .shares
        )
        assert holding_after == holding_before
        assert db_session.query(Transaction).count() == txn_count_before
