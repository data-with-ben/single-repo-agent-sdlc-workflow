"""Nightly reveal job (SPEC.md Section 10, extends T3.3).

Orchestrates the pipeline named in SPEC.md Section 10: objective engine ->
team scoring -> game winners -> write results/dividends/wallets -> recompute
prices. All of this job's real prerequisites (objective_engine, team_scoring,
game_scheduling, pricing/trading, dividends) already exist -- this module is
the thin caller each of those modules' own docstrings anticipated.

Bye-team ObjectiveResult persistence: app.models.ObjectiveResult has a non-
nullable game_id FK (a normalization added on top of SPEC.md's literal data
model), but a consultant whose team has a bye that date has no Game row to
attach to. Resolved by only persisting a DB row for consultants whose team
appears in an actual Game that date; their computed objective points still
feed team scoring in-memory for a real game if they have one, but a bye-team
consultant's points for that date are not written to the ObjectiveResult
table, since there is no valid game_id to store.

Price recompute: trading.py already computes rolling_avg_score and
demand_pressure live from ObjectiveResult/Transaction history at the moment
of any trade, rather than storing a price this job would need to refresh --
there is no persisted price value anywhere in SPEC.md's required data model
for this step to update. This step is a documented no-op under the existing
architecture: once ObjectiveResult rows are written below, any subsequent
price quote automatically reflects the new data.

Idempotency: ObjectiveResult rows for a game_date are deleted and recreated
on every run (same pattern as season.assign_teams/game_scheduling's
schedule_season_games); Game score writes are naturally idempotent
(overwriting the same deterministic fields); dividend crediting is already
idempotent by construction (task-30's per-award guard-check). Re-running for
the same game_date against unchanged TimeEntry/Game/team data produces
byte-identical results; if new TimeEntry rows are logged between two runs,
the second run legitimately reflects the new data -- not an idempotency
violation, just re-running a deterministic function against different
inputs.

Recoverable failure state (AC #3): every module in this pipeline only ever
flushes (never commits). reveal_game_date wraps its entire body in a
try/except that rolls back and re-raises on any exception, so no partial
writes are ever left in a committed state regardless of caller discipline.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.dividends import compute_dividend_awards, credit_dividends
from app.models import Dividend, Game, ObjectiveResult, TeamMembership, TimeEntry, User
from app.objective_engine import compute_objective_results
from app.team_scoring import resolve_games


@dataclass
class RevealSummary:
    objective_results_written: int
    games_finalized: int
    dividends_created: list[Dividend]


def _team_memberships_for(db: Session, team_ids: set[int]) -> dict[int, set[int]]:
    memberships = (
        db.query(TeamMembership).filter(TeamMembership.team_id.in_(team_ids)).all()
    )
    result: dict[int, set[int]] = {team_id: set() for team_id in team_ids}
    for m in memberships:
        result[m.team_id].add(m.user_id)
    return result


def reveal_game_date(db: Session, game_date: date) -> RevealSummary:
    try:
        game_date_midnight = datetime(game_date.year, game_date.month, game_date.day)
        next_day = game_date_midnight + timedelta(days=1)

        games = (
            db.query(Game)
            .filter(
                Game.game_date >= game_date_midnight, Game.game_date < next_day
            )
            .all()
        )
        team_ids = {g.home_team_id for g in games} | {g.away_team_id for g in games}
        team_memberships = _team_memberships_for(db, team_ids)
        consultant_to_team: dict[int, int] = {}
        for team_id, roster in team_memberships.items():
            for consultant_id in roster:
                consultant_to_team[consultant_id] = team_id

        consultant_to_game: dict[int, int] = {}
        for game in games:
            for team_id in (game.home_team_id, game.away_team_id):
                for consultant_id in team_memberships.get(team_id, set()):
                    consultant_to_game[consultant_id] = game.id

        entries = (
            db.query(TimeEntry)
            .filter(
                TimeEntry.work_date >= game_date_midnight,
                TimeEntry.work_date < next_day,
            )
            .all()
        )
        pto_ids = {u.id for u in db.query(User).filter(User.status == "pto").all()}

        objective_results = compute_objective_results(entries, game_date, pto_ids)

        db.query(ObjectiveResult).filter(
            ObjectiveResult.game_date == game_date_midnight
        ).delete(synchronize_session=False)

        objective_results_written = 0
        for result in objective_results:
            game_id = consultant_to_game.get(result.consultant_id)
            team_id = consultant_to_team.get(result.consultant_id)
            if game_id is None or team_id is None:
                continue  # bye-team consultant: no game to attach this row to
            db.add(
                ObjectiveResult(
                    game_id=game_id,
                    game_date=game_date_midnight,
                    consultant_id=result.consultant_id,
                    team_id=team_id,
                    projected_by_11=result.projected_by_11,
                    logged_same_day=result.logged_same_day,
                    eod_update=result.eod_update,
                    perfect_day=result.perfect_day,
                    points=result.points,
                )
            )
            objective_results_written += 1
        db.flush()

        game_results = resolve_games(objective_results, team_memberships, games)
        games_by_id = {g.id: g for g in games}
        for game_result in game_results:
            game = games_by_id[game_result.game_id]
            game.home_score = game_result.home_score
            game.away_score = game_result.away_score
            game.state = "final"
            game.revealed = True
        db.flush()

        awards = compute_dividend_awards(
            objective_results, team_memberships, game_results
        )
        dividends_created = credit_dividends(db, game_date, awards)

        db.flush()
        return RevealSummary(
            objective_results_written=objective_results_written,
            games_finalized=len(game_results),
            dividends_created=dividends_created,
        )
    except Exception:
        db.rollback()
        raise
