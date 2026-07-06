"""1v1 portfolio brackets (SPEC.md Section 11.4, task-34, optional).

SPEC.md lists this feature only as an undefined nice-to-have open decision
-- no pairing algorithm or portfolio-gain definition is given anywhere.
Resolved here, flagged for hostile review:

Participant pool: every User with a Wallet row, since seed.py already
creates one for the manager, player-manager, and every consultant -- no
one is excluded from the market, so this is the natural existing
definition of who has a portfolio to compete with. Filtered to
User.created_at <= week_end so a wallet created after the week in question
cannot retroactively change who was in that week's pool (a past week's
bracket results should stay fixed once computed, matching this app's other
point-in-time invariants).

Portfolio value at an instant = wallet balance + sum(shares held x
fair_value), using the same trading.quote_for_consultant every other price
figure in this app already uses -- never a second, independently-derived
pricing path.

Wallet.balance and Holding.shares are current-state only (the same
established pattern already used for demand_pressure and dividend
point-in-time shares). Point-in-time values here are reconstructed by
REVERSE-replaying a user's own Transaction/Dividend history backward from
the current known balance/shares, rather than forward-replaying from an
assumed starting balance constant (STARTING_BALANCE lives only in
seed.py, not a guaranteed invariant for every wallet -- one created via
trading._get_or_create_wallet starts at 0 instead). Sign table for the
reverse walk, undoing each row's effect to recover the value as it stood
strictly before as_of:

  Transaction side=buy,  executed_at > as_of:
      shares -= txn.shares   (undo the buy's credit to holdings)
      balance += txn.total   (undo the buy's debit to the wallet)
  Transaction side=sell, executed_at > as_of:
      shares += txn.shares   (undo the sell's debit to holdings)
      balance -= txn.total   (undo the sell's credit to the wallet)
  Dividend, game_date > as_of:
      balance -= dividend.total   (undo the payout's credit to the wallet)

Dividends never touch Holding.shares (dividends.py only credits Wallet
balance), so they only enter the wallet-balance reversal above.

Weekly pairing: a deterministic per-week shuffle of the participant pool,
seeded from week_start's ISO date so the same week always reproduces the
same pairing (idempotent, matching this app's other on-demand
computations) while still varying week to week -- a static permanent
pairing would undercut the rivalry premise even though AC #1 only requires
that users be "paired," not that pairings rotate. An odd pool leaves the
last shuffled participant with a bye that week, surfaced explicitly rather
than silently dropped.

Generated on demand, like weekly_wrap.py and portfolio.py -- this app has
never owned a job scheduler anywhere; some external caller is assumed to
invoke this at the right time.
"""

import random
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Dividend, Holding, Transaction, User, Wallet
from app.trading import quote_for_consultant


@dataclass
class Matchup:
    user_a_id: int
    user_b_id: int


@dataclass
class MatchupResult:
    user_a_id: int
    user_a_display_name: str
    user_a_gain: float
    user_b_id: int
    user_b_display_name: str
    user_b_gain: float
    winner_id: int | None  # None means a draw


def _wallet_balance_at(db: Session, user_id: int, as_of: datetime) -> float:
    wallet = db.get(Wallet, user_id)
    balance = wallet.balance if wallet is not None else 0.0

    later_transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id, Transaction.executed_at > as_of)
        .all()
    )
    for txn in later_transactions:
        if txn.side == "buy":
            balance += txn.total
        else:
            balance -= txn.total

    later_dividends = (
        db.query(Dividend)
        .filter(Dividend.user_id == user_id, Dividend.game_date > as_of)
        .all()
    )
    for dividend in later_dividends:
        balance -= dividend.total

    return balance


def _shares_at(
    db: Session, user_id: int, consultant_id: int, as_of: datetime
) -> int:
    holding = (
        db.query(Holding)
        .filter(Holding.user_id == user_id, Holding.consultant_id == consultant_id)
        .first()
    )
    shares = holding.shares if holding is not None else 0

    later_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.consultant_id == consultant_id,
            Transaction.executed_at > as_of,
        )
        .all()
    )
    for txn in later_transactions:
        if txn.side == "buy":
            shares -= txn.shares
        else:
            shares += txn.shares

    return shares


def _held_consultant_ids(db: Session, user_id: int) -> set[int]:
    rows = (
        db.query(Transaction.consultant_id)
        .filter(Transaction.user_id == user_id)
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def portfolio_value_at(db: Session, user_id: int, as_of: datetime) -> float:
    value = _wallet_balance_at(db, user_id, as_of)
    for consultant_id in _held_consultant_ids(db, user_id):
        shares = _shares_at(db, user_id, consultant_id, as_of)
        if shares == 0:
            continue
        quote = quote_for_consultant(db, consultant_id, as_of)
        value += shares * quote.fair_value
    return value


def portfolio_gain(
    db: Session, user_id: int, week_start: datetime, week_end: datetime
) -> float:
    return portfolio_value_at(db, user_id, week_end) - portfolio_value_at(
        db, user_id, week_start
    )


def weekly_pairings(
    db: Session, week_start: datetime
) -> tuple[list[Matchup], int | None]:
    """Returns (matchups, bye_user_id). bye_user_id is None if the pool is even."""
    wallet_user_ids = [row[0] for row in db.query(Wallet.user_id).all()]
    users = (
        db.query(User)
        .filter(User.id.in_(wallet_user_ids), User.created_at <= week_start)
        .order_by(User.id)
        .all()
    )
    user_ids = [u.id for u in users]

    rng = random.Random(week_start.date().isoformat())
    rng.shuffle(user_ids)

    bye_user_id = None
    if len(user_ids) % 2 == 1:
        bye_user_id = user_ids.pop()

    matchups = [
        Matchup(user_a_id=user_ids[i], user_b_id=user_ids[i + 1])
        for i in range(0, len(user_ids), 2)
    ]
    return matchups, bye_user_id


def resolve_matchup(
    db: Session, matchup: Matchup, week_start: datetime, week_end: datetime
) -> MatchupResult:
    user_a = db.get(User, matchup.user_a_id)
    user_b = db.get(User, matchup.user_b_id)
    gain_a = portfolio_gain(db, matchup.user_a_id, week_start, week_end)
    gain_b = portfolio_gain(db, matchup.user_b_id, week_start, week_end)

    winner_id = None
    if gain_a > gain_b:
        winner_id = matchup.user_a_id
    elif gain_b > gain_a:
        winner_id = matchup.user_b_id

    return MatchupResult(
        user_a_id=matchup.user_a_id,
        user_a_display_name=user_a.display_name,
        user_a_gain=gain_a,
        user_b_id=matchup.user_b_id,
        user_b_display_name=user_b.display_name,
        user_b_gain=gain_b,
        winner_id=winner_id,
    )


def weekly_brackets(
    db: Session, week_start: datetime, week_end: datetime
) -> tuple[list[MatchupResult], int | None]:
    """Returns (results, bye_user_id)."""
    matchups, bye_user_id = weekly_pairings(db, week_start)
    results = [resolve_matchup(db, m, week_start, week_end) for m in matchups]
    return results, bye_user_id
