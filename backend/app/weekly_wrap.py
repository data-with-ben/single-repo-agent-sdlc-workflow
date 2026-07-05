"""Weekly wrap (SPEC.md Section 9, task-33).

Team records, biggest market swing, and star performer for a week, computed
on demand over already-persisted data (Game, ObjectiveResult, and live
prices via trading.quote_for_consultant), mirroring portfolio.py's shape.

Generated on schedule (task-33's own wording): this app has never owned a
job scheduler anywhere -- reveal_game_date (task-26) is described the same
way (run at reveal time) and is likewise just a callable function some
external scheduler invokes. This module does not introduce a cron/
scheduler; generate_weekly_wrap is called on demand, matching
portfolio_summary/box_score's existing pattern.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Game, ObjectiveResult, Team, User
from app.trading import quote_for_consultant


@dataclass
class TeamRecord:
    team_id: int
    team_name: str
    wins: int
    losses: int
    draws: int


@dataclass
class MarketSwing:
    consultant_id: int
    display_name: str
    swing_pct: float


@dataclass
class StarPerformer:
    consultant_id: int
    display_name: str
    total_points: int


@dataclass
class WeeklyWrap:
    team_records: list[TeamRecord]
    biggest_market_swing: MarketSwing | None
    star_performer: StarPerformer | None


def team_records(
    db: Session, week_start: datetime, week_end: datetime
) -> list[TeamRecord]:
    games = (
        db.query(Game)
        .filter(Game.game_date >= week_start, Game.game_date < week_end)
        .all()
    )
    team_ids = {g.home_team_id for g in games} | {g.away_team_id for g in games}
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
    team_names = {t.id: t.name for t in teams}

    records = {tid: {"wins": 0, "losses": 0, "draws": 0} for tid in team_ids}
    for game in games:
        if game.home_score is None or game.away_score is None:
            continue  # postponed
        if game.home_score > game.away_score:
            records[game.home_team_id]["wins"] += 1
            records[game.away_team_id]["losses"] += 1
        elif game.away_score > game.home_score:
            records[game.away_team_id]["wins"] += 1
            records[game.home_team_id]["losses"] += 1
        else:
            records[game.home_team_id]["draws"] += 1
            records[game.away_team_id]["draws"] += 1

    return [
        TeamRecord(
            team_id=tid,
            team_name=team_names.get(tid, ""),
            wins=r["wins"],
            losses=r["losses"],
            draws=r["draws"],
        )
        for tid, r in records.items()
    ]


def biggest_market_swing(
    db: Session, week_start: datetime, week_end: datetime
) -> MarketSwing | None:
    consultants = [u for u in db.query(User).all() if "consultant" in u.roles]

    biggest: MarketSwing | None = None
    for consultant in consultants:
        start_quote = quote_for_consultant(db, consultant.id, week_start)
        end_quote = quote_for_consultant(db, consultant.id, week_end)
        if start_quote.fair_value == 0:
            continue
        swing_pct = (
            (end_quote.fair_value - start_quote.fair_value)
            / start_quote.fair_value
            * 100
        )
        if biggest is None or abs(swing_pct) > abs(biggest.swing_pct):
            biggest = MarketSwing(
                consultant_id=consultant.id,
                display_name=consultant.display_name,
                swing_pct=swing_pct,
            )

    return biggest


def star_performer(
    db: Session, week_start: datetime, week_end: datetime
) -> StarPerformer | None:
    results = (
        db.query(ObjectiveResult)
        .filter(
            ObjectiveResult.game_date >= week_start,
            ObjectiveResult.game_date < week_end,
        )
        .all()
    )
    totals: dict[int, int] = {}
    for r in results:
        totals[r.consultant_id] = totals.get(r.consultant_id, 0) + r.points

    if not totals:
        return None

    top_consultant_id = max(totals, key=lambda cid: (totals[cid], -cid))
    consultant = db.get(User, top_consultant_id)
    return StarPerformer(
        consultant_id=top_consultant_id,
        display_name=consultant.display_name,
        total_points=totals[top_consultant_id],
    )


def generate_weekly_wrap(
    db: Session, week_start: datetime, week_end: datetime
) -> WeeklyWrap:
    return WeeklyWrap(
        team_records=team_records(db, week_start, week_end),
        biggest_market_swing=biggest_market_swing(db, week_start, week_end),
        star_performer=star_performer(db, week_start, week_end),
    )
