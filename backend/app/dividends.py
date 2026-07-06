"""Dividend payout (SPEC.md Section 8).

Wires the dividend rules into the pipeline named in SPEC.md Section 10
(objective engine -> team scoring -> game winners -> write results/
dividends/wallets). task-26 (the nightly reveal job that would call this
module as one of its steps) does not exist yet, and this task's own
description says to wire dividends into it -- so this module is built as a
self-contained, directly-testable unit that task-26 becomes a thin caller
of, rather than something this task must wait on.

Point-in-time shareholding: SPEC.md Section 8 says dividends pay per share
held at end of the game date, but app.models.Holding only tracks current
shares, not historical snapshots. A holder who buys or sells between the
game date and whenever the payout actually runs would be paid against the
wrong share count if current Holding were used directly. Resolved by
reconstructing point-in-time shares from Transaction history (already a
complete, timestamped ledger): sum every matching Transaction's signed
shares (positive buy, negative sell) with executed_at before the cutoff
(the start of the day after game_date), for every user who has ever traded
that consultant. This cannot use the 30-day truncation trading.py's demand-
pressure calculation uses, since exact counts (not a decaying
approximation) are required -- O(all historical transactions per
consultant) per run, acceptable at current scale; revisit if task-26 needs
to run against much larger transaction history (e.g. via incremental
balance snapshots).

Star of the game: SPEC.md Section 8 calls this the top *normalized*
performer on the losing team. This reduces mathematically to the top
raw-points performer within that team regardless of which per-team-uniform
normalization scheme (e.g. team_scoring.py's sum/presentMemberCount) is
intended, since every teammate on the same team shares the same divisor --
dividing a team's members by a shared constant cannot change their
relative order. Ties broken by lowest consultant_id for determinism.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Dividend, Transaction, Wallet
from app.objective_engine import ObjectiveResult
from app.team_scoring import GameResult

TEAM_WIN_PER_SHARE = 2.0
PERFECT_DAY_PER_SHARE = 1.0
STAR_OF_GAME_PER_SHARE = 0.5


@dataclass
class DividendAward:
    consultant_id: int
    reason: str
    per_share: float


def _present_results(
    team_id: int,
    objective_results: list[ObjectiveResult],
    team_memberships: dict[int, set[int]],
) -> list[ObjectiveResult]:
    roster = team_memberships.get(team_id, set())
    return [r for r in objective_results if r.consultant_id in roster]


def compute_dividend_awards(
    objective_results: list[ObjectiveResult],
    team_memberships: dict[int, set[int]],
    game_results: list[GameResult],
) -> list[DividendAward]:
    awards: list[DividendAward] = []

    for result in objective_results:
        if result.perfect_day:
            awards.append(
                DividendAward(
                    result.consultant_id, "perfect_day", PERFECT_DAY_PER_SHARE
                )
            )

    for game in game_results:
        if game.postponed or game.is_draw or game.winner_team_id is None:
            continue

        winners = _present_results(
            game.winner_team_id, objective_results, team_memberships
        )
        for winner in winners:
            awards.append(
                DividendAward(winner.consultant_id, "team_win", TEAM_WIN_PER_SHARE)
            )

        loser_team_id = (
            game.away_team_id
            if game.winner_team_id == game.home_team_id
            else game.home_team_id
        )
        losers = _present_results(loser_team_id, objective_results, team_memberships)
        if losers:
            star = min(losers, key=lambda r: (-r.points, r.consultant_id))
            awards.append(
                DividendAward(
                    star.consultant_id, "star_of_game", STAR_OF_GAME_PER_SHARE
                )
            )

    return awards


def _shares_held_as_of(
    db: Session, user_id: int, consultant_id: int, cutoff: datetime
) -> int:
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.consultant_id == consultant_id,
            Transaction.executed_at < cutoff,
        )
        .all()
    )
    return sum(t.shares if t.side == "buy" else -t.shares for t in transactions)


def _shareholders_as_of(
    db: Session, consultant_id: int, cutoff: datetime
) -> dict[int, int]:
    user_ids = {
        row[0]
        for row in db.query(Transaction.user_id)
        .filter(Transaction.consultant_id == consultant_id)
        .distinct()
        .all()
    }
    holdings = {
        user_id: _shares_held_as_of(db, user_id, consultant_id, cutoff)
        for user_id in user_ids
    }
    return {user_id: shares for user_id, shares in holdings.items() if shares > 0}


def _get_or_create_wallet(db: Session, user_id: int) -> Wallet:
    wallet = db.get(Wallet, user_id)
    if wallet is None:
        wallet = Wallet(user_id=user_id, balance=0.0)
        db.add(wallet)
        db.flush()
    return wallet


def credit_dividends(
    db: Session, game_date: date, awards: list[DividendAward]
) -> list[Dividend]:
    game_date_midnight = datetime(game_date.year, game_date.month, game_date.day)
    cutoff = game_date_midnight + timedelta(days=1)

    created: list[Dividend] = []
    for award in awards:
        shareholders = _shareholders_as_of(db, award.consultant_id, cutoff)
        for user_id, shares in shareholders.items():
            already_paid = (
                db.query(Dividend)
                .filter(
                    Dividend.user_id == user_id,
                    Dividend.consultant_id == award.consultant_id,
                    Dividend.game_date == game_date_midnight,
                    Dividend.reason == award.reason,
                )
                .first()
            )
            if already_paid is not None:
                continue

            total = shares * award.per_share
            wallet = _get_or_create_wallet(db, user_id)
            wallet.balance += total

            dividend = Dividend(
                user_id=user_id,
                consultant_id=award.consultant_id,
                game_date=game_date_midnight,
                reason=award.reason,
                shares=shares,
                per_share=award.per_share,
                total=total,
            )
            db.add(dividend)
            created.append(dividend)

    db.flush()
    return created


def dividend_feed(db: Session, user_id: int, limit: int = 50) -> list[Dividend]:
    return (
        db.query(Dividend)
        .filter(Dividend.user_id == user_id)
        .order_by(Dividend.game_date.desc(), Dividend.id.desc())
        .limit(limit)
        .all()
    )
