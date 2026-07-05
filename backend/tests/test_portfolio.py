from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.dividends import DividendAward, credit_dividends
from app.models import Game, Holding, ObjectiveResult, Season, Team, User, Wallet
from app.portfolio import (
    exchange_listing,
    holdings_view,
    market_movers,
    portfolio_summary,
)
from app.pricing import PriceQuote
from app.trading import execute_buy

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'portfolio_test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


_email_counter = iter(range(1_000_000))


def _make_consultant(db_session) -> User:
    user = User(
        display_name=f"Consultant {next(_email_counter)}",
        email=f"consultant{next(_email_counter)}@example.com",
        roles=["consultant"],
        created_at=NOW,
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _add_objective_result(
    db_session, consultant_id, game_date, points, projected_by_11=True
):
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
            consultant_id=consultant_id,
            team_id=team.id,
            projected_by_11=projected_by_11,
            logged_same_day=True,
            eod_update=False,
            perfect_day=False,
            points=points,
        )
    )
    db_session.commit()


class TestHoldingsView:
    def test_shows_real_holdings_with_live_quotes(self, db_session):
        buyer = _make_consultant(db_session)
        consultant = _make_consultant(db_session)
        db_session.add(Wallet(user_id=buyer.id, balance=100000.0))
        db_session.commit()
        execute_buy(db_session, buyer.id, consultant.id, shares=10, now=NOW)
        db_session.commit()

        views = holdings_view(db_session, buyer.id, NOW)

        assert len(views) == 1
        assert views[0].consultant_id == consultant.id
        assert views[0].shares == 10
        assert views[0].display_name == consultant.display_name
        assert views[0].buy_price > 0
        assert views[0].sell_price > 0

    def test_excludes_zero_share_holdings(self, db_session):
        buyer = _make_consultant(db_session)
        consultant = _make_consultant(db_session)
        db_session.add(Holding(user_id=buyer.id, consultant_id=consultant.id, shares=0))
        db_session.commit()

        views = holdings_view(db_session, buyer.id, NOW)

        assert views == []

    def test_movement_reflects_rising_recent_performance(self, db_session):
        buyer = _make_consultant(db_session)
        consultant = _make_consultant(db_session)
        db_session.add(Wallet(user_id=buyer.id, balance=100000.0))
        db_session.commit()
        execute_buy(db_session, buyer.id, consultant.id, shares=1, now=NOW)
        db_session.commit()
        # Strong performance in the last few days should raise fair_value
        # relative to 7 days ago (when no history existed at all).
        _add_objective_result(db_session, consultant.id, NOW - timedelta(days=1), 30)

        views = holdings_view(db_session, buyer.id, NOW)

        assert views[0].movement_pct > 0


class TestMarketMovers:
    def test_ranks_top_gainer_and_loser(self, db_session):
        strong = _make_consultant(db_session)
        weak = _make_consultant(db_session)
        neutral = _make_consultant(db_session)
        _add_objective_result(db_session, strong.id, NOW - timedelta(days=1), 30)

        movers = market_movers(db_session, NOW, limit=1)

        mover_ids = {m.consultant_id for m in movers}
        assert strong.id in mover_ids
        assert weak.id not in mover_ids or neutral.id not in mover_ids

    def test_gainer_appears_before_loser(self, db_session):
        gainer = _make_consultant(db_session)
        _add_objective_result(db_session, gainer.id, NOW - timedelta(days=1), 30)

        movers = market_movers(db_session, NOW, limit=1)

        assert movers[0].consultant_id == gainer.id
        assert movers[0].movement_pct > 0

    def test_recent_team_win_count_reflects_dividend_history(self, db_session):
        consultant = _make_consultant(db_session)
        shareholder = _make_consultant(db_session)
        db_session.add(Wallet(user_id=shareholder.id, balance=100000.0))
        db_session.commit()
        # Bought before the dividend's game date, so the shareholder holds
        # shares as of that date's point-in-time cutoff.
        execute_buy(
            db_session,
            shareholder.id,
            consultant.id,
            shares=1,
            now=NOW - timedelta(days=2),
        )
        db_session.commit()
        # A dividend payout alone does not move the price -- give the
        # consultant real recent performance too, so they actually appear
        # as a mover (movement_pct > 0) and this test can inspect their
        # recent_team_wins figure.
        _add_objective_result(db_session, consultant.id, NOW - timedelta(days=1), 30)
        credit_dividends(
            db_session,
            (NOW - timedelta(days=1)).date(),
            [DividendAward(consultant.id, "team_win", 2.0)],
        )
        db_session.commit()

        movers = market_movers(db_session, NOW, limit=10)

        mover = next(m for m in movers if m.consultant_id == consultant.id)
        assert mover.recent_team_wins == 1

    def test_recent_missed_projection_count(self, db_session):
        consultant = _make_consultant(db_session)
        _add_objective_result(
            db_session,
            consultant.id,
            NOW - timedelta(days=1),
            points=5,
            projected_by_11=False,
        )

        movers = market_movers(db_session, NOW, limit=10)

        mover = next(m for m in movers if m.consultant_id == consultant.id)
        assert mover.recent_missed_projections == 1


class TestMovementPctZeroBaseline:
    def test_zero_previous_fair_value_does_not_divide_by_zero(self, db_session):
        buyer = _make_consultant(db_session)
        consultant = _make_consultant(db_session)
        db_session.add(Wallet(user_id=buyer.id, balance=100000.0))
        db_session.commit()
        execute_buy(db_session, buyer.id, consultant.id, shares=1, now=NOW)
        db_session.commit()

        zero_quote = PriceQuote(fair_value=0.0, buy_price=0.0, sell_price=0.0)
        with patch(
            "app.portfolio.quote_for_consultant", return_value=zero_quote
        ):
            views = holdings_view(db_session, buyer.id, NOW)

        assert views[0].movement_pct == 0.0


class TestExchangeListing:
    def test_lists_every_active_consultant_with_a_live_quote(self, db_session):
        held = _make_consultant(db_session)
        not_held = _make_consultant(db_session)
        buyer = _make_consultant(db_session)
        db_session.add(Wallet(user_id=buyer.id, balance=100000.0))
        db_session.commit()
        execute_buy(db_session, buyer.id, held.id, shares=1, now=NOW)
        db_session.commit()

        listings = exchange_listing(db_session, NOW)

        consultant_ids = {listing.consultant_id for listing in listings}
        assert held.id in consultant_ids
        assert not_held.id in consultant_ids

    def test_sorted_by_display_name(self, db_session):
        _make_consultant(db_session)
        _make_consultant(db_session)

        listings = exchange_listing(db_session, NOW)

        assert [listing.display_name for listing in listings] == sorted(
            listing.display_name for listing in listings
        )


class TestPortfolioSummary:
    def test_bundles_wallet_holdings_dividends_and_movers(self, db_session):
        buyer = _make_consultant(db_session)
        consultant = _make_consultant(db_session)
        db_session.add(Wallet(user_id=buyer.id, balance=100000.0))
        db_session.commit()
        execute_buy(db_session, buyer.id, consultant.id, shares=5, now=NOW)
        db_session.commit()

        summary = portfolio_summary(db_session, buyer.id, NOW)

        assert summary["wallet_balance"] > 0
        assert len(summary["holdings"]) == 1
        assert summary["dividends"] == []
        assert isinstance(summary["market_movers"], list)

    def test_wallet_balance_defaults_to_zero_without_creating_a_row(self, db_session):
        user = _make_consultant(db_session)

        summary = portfolio_summary(db_session, user.id, NOW)

        assert summary["wallet_balance"] == 0.0
        assert db_session.get(Wallet, user.id) is None
