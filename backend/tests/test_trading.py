from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Game,
    Holding,
    ObjectiveResult,
    Season,
    Team,
    Transaction,
    User,
    Wallet,
)
from app.pricing import price_quote
from app.trading import OWNERSHIP_CAP_SHARES, execute_buy, execute_sell

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'trading_test.db'}")
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
        created_at=NOW,
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _fund_wallet(db_session, user_id, balance) -> Wallet:
    wallet = Wallet(user_id=user_id, balance=balance)
    db_session.add(wallet)
    db_session.commit()
    return wallet


def _base_price(db_session, consultant_id, as_of=NOW):
    # No ObjectiveResult / Transaction history -> rolling_avg_score=0,
    # demand_pressure=0 -> the bare BASE fair value quote.
    return price_quote(rolling_avg_score=0.0, demand_pressure=0.0)


class TestBuyDebitsWallet:
    def test_buy_debits_wallet_at_quoted_price(self, db_session):
        buyer = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, buyer.id, balance=1000.0)
        expected_quote = _base_price(db_session, consultant.id)

        execute_buy(db_session, buyer.id, consultant.id, shares=5, now=NOW)
        db_session.commit()

        wallet = db_session.get(Wallet, buyer.id)
        assert wallet.balance == pytest.approx(1000.0 - 5 * expected_quote.buy_price)


class TestSellCreditsWallet:
    def test_sell_credits_wallet_at_quoted_price(self, db_session):
        seller = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, seller.id, balance=0.0)
        db_session.add(
            Holding(user_id=seller.id, consultant_id=consultant.id, shares=10)
        )
        db_session.commit()
        expected_quote = _base_price(db_session, consultant.id)

        execute_sell(db_session, seller.id, consultant.id, shares=4, now=NOW)
        db_session.commit()

        wallet = db_session.get(Wallet, seller.id)
        assert wallet.balance == pytest.approx(4 * expected_quote.sell_price)


class TestOwnershipCap:
    def test_buying_up_to_the_cap_succeeds(self, db_session):
        buyer = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, buyer.id, balance=100000.0)

        execute_buy(
            db_session, buyer.id, consultant.id, shares=OWNERSHIP_CAP_SHARES, now=NOW
        )
        db_session.commit()

        holding = (
            db_session.query(Holding)
            .filter(
                Holding.user_id == buyer.id, Holding.consultant_id == consultant.id
            )
            .one()
        )
        assert holding.shares == OWNERSHIP_CAP_SHARES

    def test_exceeding_the_cap_is_rejected(self, db_session):
        buyer = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, buyer.id, balance=100000.0)
        execute_buy(
            db_session, buyer.id, consultant.id, shares=OWNERSHIP_CAP_SHARES, now=NOW
        )
        db_session.commit()

        with pytest.raises(ValueError):
            execute_buy(db_session, buyer.id, consultant.id, shares=1, now=NOW)

    def test_cap_applies_against_self_purchase(self, db_session):
        consultant = _make_user(db_session)
        _fund_wallet(db_session, consultant.id, balance=100000.0)

        with pytest.raises(ValueError):
            execute_buy(
                db_session,
                consultant.id,
                consultant.id,
                shares=OWNERSHIP_CAP_SHARES + 1,
                now=NOW,
            )

        holding = (
            db_session.query(Holding)
            .filter(
                Holding.user_id == consultant.id,
                Holding.consultant_id == consultant.id,
            )
            .first()
        )
        assert holding is None or holding.shares == 0


class TestOverspendAndOversellRejected:
    def test_overspend_is_rejected_and_state_is_unchanged(self, db_session):
        buyer = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, buyer.id, balance=1.0)

        with pytest.raises(ValueError):
            execute_buy(db_session, buyer.id, consultant.id, shares=1000, now=NOW)

        wallet = db_session.get(Wallet, buyer.id)
        assert wallet.balance == 1.0
        assert db_session.query(Transaction).count() == 0

    def test_oversell_is_rejected_and_state_is_unchanged(self, db_session):
        seller = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, seller.id, balance=0.0)
        db_session.add(
            Holding(user_id=seller.id, consultant_id=consultant.id, shares=3)
        )
        db_session.commit()

        with pytest.raises(ValueError):
            execute_sell(db_session, seller.id, consultant.id, shares=4, now=NOW)

        holding = (
            db_session.query(Holding)
            .filter(
                Holding.user_id == seller.id, Holding.consultant_id == consultant.id
            )
            .one()
        )
        assert holding.shares == 3
        wallet = db_session.get(Wallet, seller.id)
        assert wallet.balance == 0.0
        assert db_session.query(Transaction).count() == 0

    def test_selling_with_no_holding_at_all_is_rejected(self, db_session):
        seller = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, seller.id, balance=0.0)

        with pytest.raises(ValueError):
            execute_sell(db_session, seller.id, consultant.id, shares=1, now=NOW)

    def test_buy_with_no_existing_wallet_row_is_created_and_still_enforces_balance(
        self, db_session
    ):
        buyer = _make_user(db_session)
        consultant = _make_user(db_session)
        # No _fund_wallet call: the wallet row does not exist yet.

        with pytest.raises(ValueError):
            execute_buy(db_session, buyer.id, consultant.id, shares=1, now=NOW)

        wallet = db_session.get(Wallet, buyer.id)
        assert wallet is not None
        assert wallet.balance == 0.0


class TestTransactionRecording:
    def test_successful_buy_records_one_transaction(self, db_session):
        buyer = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, buyer.id, balance=1000.0)

        txn = execute_buy(db_session, buyer.id, consultant.id, shares=3, now=NOW)
        db_session.commit()

        assert db_session.query(Transaction).count() == 1
        assert txn.side == "buy"
        assert txn.shares == 3
        assert txn.total == pytest.approx(3 * txn.price_per_share)
        assert txn.executed_at == NOW

    def test_successful_sell_records_one_transaction(self, db_session):
        seller = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, seller.id, balance=0.0)
        db_session.add(
            Holding(user_id=seller.id, consultant_id=consultant.id, shares=5)
        )
        db_session.commit()

        txn = execute_sell(db_session, seller.id, consultant.id, shares=2, now=NOW)
        db_session.commit()

        assert db_session.query(Transaction).count() == 1
        assert txn.side == "sell"
        assert txn.shares == 2
        assert txn.total == pytest.approx(2 * txn.price_per_share)


class TestInputValidation:
    def test_buy_zero_shares_rejected(self, db_session):
        buyer = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, buyer.id, balance=1000.0)

        with pytest.raises(ValueError):
            execute_buy(db_session, buyer.id, consultant.id, shares=0, now=NOW)

    def test_sell_negative_shares_rejected(self, db_session):
        seller = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, seller.id, balance=0.0)

        with pytest.raises(ValueError):
            execute_sell(db_session, seller.id, consultant.id, shares=-1, now=NOW)


class TestPriceSourcing:
    def _make_objective_result(self, db_session, consultant, game_date, points):
        season = Season(
            name="S",
            start_date=game_date,
            end_date=game_date + timedelta(days=1),
            status="active",
            team_size=4,
        )
        db_session.add(season)
        db_session.flush()
        team = Team(season_id=season.id, name="T")
        db_session.add(team)
        db_session.flush()
        game = Game(
            game_date=game_date,
            season_id=season.id,
            home_team_id=team.id,
            away_team_id=team.id,
            state="final",
            revealed=True,
        )
        db_session.add(game)
        db_session.flush()
        db_session.add(
            ObjectiveResult(
                game_id=game.id,
                game_date=game_date,
                consultant_id=consultant.id,
                team_id=team.id,
                points=points,
            )
        )
        db_session.commit()

    def test_strong_recent_history_prices_higher_than_no_history(self, db_session):
        buyer = _make_user(db_session)
        strong_consultant = _make_user(db_session)
        weak_consultant = _make_user(db_session)
        _fund_wallet(db_session, buyer.id, balance=100000.0)

        self._make_objective_result(
            db_session, strong_consultant, NOW - timedelta(days=1), 30
        )

        strong_txn = execute_buy(
            db_session, buyer.id, strong_consultant.id, shares=1, now=NOW
        )
        weak_txn = execute_buy(
            db_session, buyer.id, weak_consultant.id, shares=1, now=NOW
        )
        db_session.commit()

        assert strong_txn.price_per_share > weak_txn.price_per_share

    def test_a_sequence_of_buys_raises_the_quoted_price(self, db_session):
        buyer = _make_user(db_session)
        consultant = _make_user(db_session)
        _fund_wallet(db_session, buyer.id, balance=100000.0)

        first_txn = execute_buy(db_session, buyer.id, consultant.id, shares=5, now=NOW)
        db_session.commit()
        second_txn = execute_buy(
            db_session, buyer.id, consultant.id, shares=5, now=NOW + timedelta(hours=1)
        )
        db_session.commit()

        assert second_txn.price_per_share > first_txn.price_per_share
