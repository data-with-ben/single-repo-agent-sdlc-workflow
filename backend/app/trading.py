"""Buy/sell execution and wallet (SPEC.md Section 8).

Executes trades against T4.1's pricing module, enforcing the ownership cap
and wallet balance, and records every trade as a Transaction. DB-writing
service functions (real I/O), following the same shape as season.py and
game_scheduling.py.

Sourcing the quoted price: pricing.price_quote takes rolling_avg_score and
demand_pressure as plain floats -- computed by whichever caller has DB
access. No caller (task-26, the nightly reveal job) exists yet to maintain
a persisted, incrementally-updated price or demand-pressure value, and
SPEC.md Section 4 (REQUIRED CONTEXT)'s data model has no slot to store one.
Resolved here by computing both live, at trade time, purely from data that
already exists in the required model:

- rolling_avg_score: the trailing 10 calendar days of ObjectiveResult rows
  for the traded consultant, ending on and including the trade's own date,
  averaged; 0.0 if no rows exist yet (a new consultant with no game history
  prices at the bare BASE fair value).
- demand_pressure: that consultant's own Transaction history (across all
  buyers -- demand pressure is a per-consultant market attribute, not
  per-buyer), replayed in chronological order through pricing's
  decay_demand_pressure + apply_trade_pressure, decaying for the elapsed
  days between each consecutive transaction and then applying its net
  shares (buy positive, sell negative). Bounded to the trailing 30 days:
  decay_rate=0.8 renders anything older negligible (0.8**30 ~= 0.001), so
  this avoids an ever-growing query as the system ages with no correctness
  cost.

A Holding row is left at shares=0 after a full sell rather than deleted,
so a subsequent buy does not need re-creation logic.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Holding, ObjectiveResult, Season, Transaction, User, Wallet
from app.pricing import (
    PriceQuote,
    apply_trade_pressure,
    decay_demand_pressure,
    price_quote,
)

TOTAL_SUPPLY_PER_CONSULTANT = 100
OWNERSHIP_CAP_FRACTION = 0.25
OWNERSHIP_CAP_SHARES = int(TOTAL_SUPPLY_PER_CONSULTANT * OWNERSHIP_CAP_FRACTION)

ROLLING_AVG_WINDOW_DAYS = 10
DEMAND_PRESSURE_WINDOW_DAYS = 30


def _rolling_avg_score(db: Session, consultant_id: int, as_of: datetime) -> float:
    window_start = as_of - timedelta(days=ROLLING_AVG_WINDOW_DAYS)
    results = (
        db.query(ObjectiveResult)
        .filter(
            ObjectiveResult.consultant_id == consultant_id,
            ObjectiveResult.game_date > window_start,
            ObjectiveResult.game_date <= as_of,
        )
        .all()
    )
    if not results:
        return 0.0
    return sum(r.points for r in results) / len(results)


def _current_demand_pressure(db: Session, consultant_id: int, as_of: datetime) -> float:
    window_start = as_of - timedelta(days=DEMAND_PRESSURE_WINDOW_DAYS)
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.consultant_id == consultant_id,
            Transaction.executed_at > window_start,
            Transaction.executed_at <= as_of,
        )
        .order_by(Transaction.executed_at)
        .all()
    )

    pressure = 0.0
    last_update = window_start
    for txn in transactions:
        days_elapsed = (txn.executed_at - last_update).days
        pressure = decay_demand_pressure(pressure, days_elapsed)
        net_shares = txn.shares if txn.side == "buy" else -txn.shares
        pressure = apply_trade_pressure(pressure, net_shares)
        last_update = txn.executed_at

    days_elapsed = (as_of - last_update).days
    return decay_demand_pressure(pressure, days_elapsed)


def quote_for_consultant(
    db: Session, consultant_id: int, as_of: datetime
) -> PriceQuote:
    rolling_avg_score = _rolling_avg_score(db, consultant_id, as_of)
    demand_pressure = _current_demand_pressure(db, consultant_id, as_of)
    return price_quote(rolling_avg_score, demand_pressure)


def is_tradable(db: Session, consultant_id: int) -> bool:
    """SPEC.md Section 8: a new hire enters the market with fresh supply at
    the start of the next season, not immediately. No new persisted state
    is needed -- Season.start_date and User.created_at (both already in the
    required data model) are sufficient: a consultant is tradable once a
    season has started on or after their hire date. Depends only on which
    Season is currently marked active (a stored, authoritative flag set by
    season.start_new_season), not on the caller's "now" -- matching how the
    rest of this codebase already treats active status, not date math
    against the clock, as the source of truth for which season is current.
    """
    active_season = (
        db.query(Season)
        .filter(Season.status == "active")
        .order_by(Season.start_date.desc())
        .first()
    )
    if active_season is None:
        return True

    consultant = db.get(User, consultant_id)
    return consultant.created_at <= active_season.start_date


def _get_or_create_wallet(db: Session, user_id: int) -> Wallet:
    wallet = db.get(Wallet, user_id)
    if wallet is None:
        wallet = Wallet(user_id=user_id, balance=0.0)
        db.add(wallet)
        db.flush()
    return wallet


def _get_or_create_holding(db: Session, user_id: int, consultant_id: int) -> Holding:
    holding = (
        db.query(Holding)
        .filter(Holding.user_id == user_id, Holding.consultant_id == consultant_id)
        .first()
    )
    if holding is None:
        holding = Holding(user_id=user_id, consultant_id=consultant_id, shares=0)
        db.add(holding)
        db.flush()
    return holding


def execute_buy(
    db: Session, user_id: int, consultant_id: int, shares: int, now: datetime
) -> Transaction:
    if shares <= 0:
        raise ValueError("shares must be positive")

    if not is_tradable(db, consultant_id):
        raise ValueError(
            "this consultant is not yet tradable -- new hires enter the "
            "market at the next season boundary"
        )

    quote = quote_for_consultant(db, consultant_id, now)
    total_cost = shares * quote.buy_price

    wallet = _get_or_create_wallet(db, user_id)
    if wallet.balance < total_cost:
        raise ValueError("insufficient wallet balance for this purchase")

    holding = _get_or_create_holding(db, user_id, consultant_id)
    if holding.shares + shares > OWNERSHIP_CAP_SHARES:
        raise ValueError(
            f"purchase would exceed the ownership cap of {OWNERSHIP_CAP_SHARES} shares"
        )

    wallet.balance -= total_cost
    holding.shares += shares

    txn = Transaction(
        user_id=user_id,
        consultant_id=consultant_id,
        side="buy",
        shares=shares,
        price_per_share=quote.buy_price,
        total=total_cost,
        executed_at=now,
    )
    db.add(txn)
    db.flush()
    return txn


def execute_sell(
    db: Session, user_id: int, consultant_id: int, shares: int, now: datetime
) -> Transaction:
    if shares <= 0:
        raise ValueError("shares must be positive")

    holding = _get_or_create_holding(db, user_id, consultant_id)
    if holding.shares < shares:
        raise ValueError("cannot sell more shares than are held")

    quote = quote_for_consultant(db, consultant_id, now)
    total_proceeds = shares * quote.sell_price

    wallet = _get_or_create_wallet(db, user_id)
    wallet.balance += total_proceeds
    holding.shares -= shares

    txn = Transaction(
        user_id=user_id,
        consultant_id=consultant_id,
        side="sell",
        shares=shares,
        price_per_share=quote.sell_price,
        total=total_proceeds,
        executed_at=now,
    )
    db.add(txn)
    db.flush()
    return txn
