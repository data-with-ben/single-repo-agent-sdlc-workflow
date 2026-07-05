"""Portfolio and exchange (SPEC.md Section 9 screen 5, wireframe 5).

Holdings view, market movers, and the 7-day movement figure both need,
matching the wireframe's Your portfolio and Market movers sections. Reuses
trading.quote_for_consultant for every price shown here -- the same
function execute_buy/execute_sell charge against -- rather than a second,
independently-derived pricing path that could silently drift from the real
transaction price.

Market movers: SPEC.md Section 9 names movers in the screen list but never
defines how they are ranked or what their descriptive blurb should say.
Resolved here as the top gainers/losers by 7-day fair_value percentage
change across every active consultant, with a short blurb (recent team_win
count, recent missed-projection count) computed from data that already
exists in the required model. A PTO-return detector like the wireframe's
example is not attempted, since historical status-change tracking does not
exist anywhere in the required data model.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.dividends import Dividend, dividend_feed
from app.models import Holding, ObjectiveResult, User, Wallet
from app.trading import quote_for_consultant

MOVEMENT_WINDOW_DAYS = 7
DEFAULT_MOVERS_LIMIT = 3


@dataclass
class HoldingView:
    consultant_id: int
    display_name: str
    shares: int
    buy_price: float
    sell_price: float
    movement_pct: float


@dataclass
class MoverView:
    consultant_id: int
    display_name: str
    movement_pct: float
    recent_team_wins: int
    recent_missed_projections: int


@dataclass
class ExchangeListing:
    consultant_id: int
    display_name: str
    buy_price: float
    sell_price: float


def _movement_pct(db: Session, consultant_id: int, now: datetime) -> float:
    current = quote_for_consultant(db, consultant_id, now)
    previous = quote_for_consultant(
        db, consultant_id, now - timedelta(days=MOVEMENT_WINDOW_DAYS)
    )
    if previous.fair_value == 0:
        return 0.0
    return (current.fair_value - previous.fair_value) / previous.fair_value * 100


def wallet_balance(db: Session, user_id: int) -> float:
    wallet = db.get(Wallet, user_id)
    return wallet.balance if wallet is not None else 0.0


def holdings_view(db: Session, user_id: int, now: datetime) -> list[HoldingView]:
    holdings = (
        db.query(Holding)
        .filter(Holding.user_id == user_id, Holding.shares > 0)
        .all()
    )
    consultant_ids = {h.consultant_id for h in holdings}
    display_names = {
        u.id: u.display_name
        for u in db.query(User).filter(User.id.in_(consultant_ids)).all()
    }

    views = []
    for holding in holdings:
        quote = quote_for_consultant(db, holding.consultant_id, now)
        views.append(
            HoldingView(
                consultant_id=holding.consultant_id,
                display_name=display_names.get(holding.consultant_id, ""),
                shares=holding.shares,
                buy_price=quote.buy_price,
                sell_price=quote.sell_price,
                movement_pct=_movement_pct(db, holding.consultant_id, now),
            )
        )
    return views


def market_movers(
    db: Session, now: datetime, limit: int = DEFAULT_MOVERS_LIMIT
) -> list[MoverView]:
    consultants = [u for u in db.query(User).all() if "consultant" in u.roles]
    window_start = now - timedelta(days=MOVEMENT_WINDOW_DAYS)

    movers = []
    for consultant in consultants:
        recent_results = (
            db.query(ObjectiveResult)
            .filter(
                ObjectiveResult.consultant_id == consultant.id,
                ObjectiveResult.game_date > window_start,
                ObjectiveResult.game_date <= now,
            )
            .all()
        )
        recent_missed = sum(1 for r in recent_results if not r.projected_by_11)
        recent_win_dividends = (
            db.query(Dividend)
            .filter(
                Dividend.consultant_id == consultant.id,
                Dividend.reason == "team_win",
                Dividend.game_date > window_start,
                Dividend.game_date <= now,
            )
            .all()
        )
        recent_wins = len({d.game_date for d in recent_win_dividends})
        movers.append(
            MoverView(
                consultant_id=consultant.id,
                display_name=consultant.display_name,
                movement_pct=_movement_pct(db, consultant.id, now),
                recent_team_wins=recent_wins,
                recent_missed_projections=recent_missed,
            )
        )

    ranked = sorted(movers, key=lambda m: m.movement_pct, reverse=True)
    gainers = [m for m in ranked if m.movement_pct > 0][:limit]
    losers = [m for m in ranked if m.movement_pct < 0][-limit:][::-1]
    return gainers + losers


def exchange_listing(db: Session, now: datetime) -> list[ExchangeListing]:
    """Every active consultant with a live quote, for the wireframe's
    Browse the exchange action -- discovering and buying a consultant not
    currently held, not just trading existing holdings.
    """
    consultants = [u for u in db.query(User).all() if "consultant" in u.roles]
    listings = []
    for consultant in consultants:
        quote = quote_for_consultant(db, consultant.id, now)
        listings.append(
            ExchangeListing(
                consultant_id=consultant.id,
                display_name=consultant.display_name,
                buy_price=quote.buy_price,
                sell_price=quote.sell_price,
            )
        )
    return sorted(listings, key=lambda listing: listing.display_name)


def portfolio_summary(db: Session, user_id: int, now: datetime) -> dict:
    return {
        "wallet_balance": wallet_balance(db, user_id),
        "holdings": holdings_view(db, user_id, now),
        "dividends": dividend_feed(db, user_id),
        "market_movers": market_movers(db, now),
    }
