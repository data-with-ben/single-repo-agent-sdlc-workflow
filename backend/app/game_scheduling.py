"""Game scheduling (SPEC.md Section 7).

Generates the season's game schedule: one round-robin matchup set per
workday (Mon-Fri, matching app.seed's existing workday convention), with a
bye for whichever team sits out when the team count is odd.

Byes: app.models.Game has non-nullable home_team_id/away_team_id, so there
is no schema support for a one-sided "bye" row. team_scoring.py's own
docstring already documents the resolved interpretation that a bye is the
absence of a Game row for that team/date -- this module follows the same
interpretation for consistency with that already-built downstream
consumer, but additionally returns byes as an explicit {date: team_id}
mapping so callers and tests can assert on them directly rather than only
by absence.

Balance: cycling the round-robin cycle across the season's full workday
list guarantees every team's game/bye count is identical after any whole
number of cycles, and differs by at most one team across the season if the
season length is not an exact multiple of the cycle length (the maximum
achievable balance without a more complex scheduling algorithm).

season.end_date is treated as inclusive: the schedule covers every workday
from start_date through end_date, both ends included.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Game, Season, Team


def _workdays(start_date: datetime, end_date: datetime) -> list[datetime]:
    workdays = []
    cursor = start_date
    while cursor.date() <= end_date.date():
        if cursor.weekday() < 5:  # Mon-Fri
            workdays.append(cursor)
        cursor += timedelta(days=1)
    return workdays


def _round_robin_rounds(team_ids: list[int]) -> list[list[tuple[int, int]]]:
    """Circle method: returns one list of (team_a, team_b) pairs per round.

    A team_id of None is a sentinel bye slot used to make an odd team count
    even; whichever real team is paired with it in a round is that round's
    bye and produces no pairing entry.
    """
    ids: list[int | None] = list(team_ids)
    if len(ids) % 2 == 1:
        ids.append(None)

    n = len(ids)
    rounds = []
    fixed = ids[0]
    rotating = ids[1:]
    for _ in range(n - 1):
        current = [fixed] + rotating
        pairs = []
        for i in range(n // 2):
            a, b = current[i], current[n - 1 - i]
            if a is not None and b is not None:
                pairs.append((a, b))
        rounds.append(pairs)
        rotating = [rotating[-1]] + rotating[:-1]
    return rounds


def _bye_team(team_ids: list[int], round_pairs: list[tuple[int, int]]) -> int | None:
    if len(team_ids) % 2 == 0:
        return None
    paired = {t for pair in round_pairs for t in pair}
    remaining = [t for t in team_ids if t not in paired]
    return remaining[0] if remaining else None


def build_schedule(
    team_ids: list[int], workdays: list[datetime]
) -> tuple[list[tuple[datetime, int, int]], dict[datetime, int]]:
    """Pure function: returns (games, byes).

    games is a list of (game_date, home_team_id, away_team_id) tuples.
    byes is a {game_date: bye_team_id} mapping, present only for dates
    where the team count is odd.
    """
    if len(team_ids) < 2:
        raise ValueError("At least 2 teams are required to schedule games")

    rounds = _round_robin_rounds(team_ids)
    games: list[tuple[datetime, int, int]] = []
    byes: dict[datetime, int] = {}

    for i, workday in enumerate(workdays):
        round_pairs = rounds[i % len(rounds)]
        for home_id, away_id in round_pairs:
            games.append((workday, home_id, away_id))
        bye_team = _bye_team(team_ids, round_pairs)
        if bye_team is not None:
            byes[workday] = bye_team

    return games, byes


def schedule_season_games(
    db: Session, season: Season
) -> tuple[list[Game], dict[datetime, int]]:
    """DB-writing wrapper. Deletes any previously scheduled games for this
    season before regenerating, so re-running scheduling for the same
    season is idempotent rather than accumulating duplicate Game rows.
    """
    db.query(Game).filter(Game.season_id == season.id).delete(
        synchronize_session=False
    )
    db.flush()

    teams = db.query(Team).filter(Team.season_id == season.id).order_by(Team.id).all()
    team_ids = [t.id for t in teams]

    workdays = _workdays(season.start_date, season.end_date)
    scheduled, byes = build_schedule(team_ids, workdays)

    created_games = []
    for game_date, home_id, away_id in scheduled:
        game = Game(
            game_date=game_date,
            season_id=season.id,
            home_team_id=home_id,
            away_team_id=away_id,
            state="scheduled",
            revealed=False,
        )
        db.add(game)
        created_games.append(game)

    db.flush()
    return created_games, byes
