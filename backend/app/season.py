"""Season creation and team assignment (SPEC.md Section 7).

Service-layer functions with real DB I/O, unlike objective_engine.py/
team_scoring.py -- nothing in this task's acceptance criteria describes an
HTTP request/response shape, so this is implemented as callable functions
rather than a new route.

Mid-season joins/new hires are explicitly out of scope: a separate, later
task (new-hire IPO at season boundaries) owns that concern. This module
only assigns the active roster at the moment a season starts.
"""

import math
import random
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Season, Team, TeamMembership, User

MIN_TEAM_SIZE = 3
MAX_TEAM_SIZE = 5


def create_season(
    db: Session, name: str, start_date: datetime, end_date: datetime, team_size: int
) -> Season:
    if not (MIN_TEAM_SIZE <= team_size <= MAX_TEAM_SIZE):
        raise ValueError(
            f"team_size must be between {MIN_TEAM_SIZE} and {MAX_TEAM_SIZE}"
        )

    season = Season(
        name=name,
        start_date=start_date,
        end_date=end_date,
        status="upcoming",
        team_size=team_size,
    )
    db.add(season)
    db.flush()
    return season


def _active_consultants(db: Session) -> list[User]:
    users = db.query(User).filter(User.status == "active").all()
    return [u for u in users if "consultant" in u.roles]


def _team_sizes(total: int, team_size: int) -> list[int]:
    min_teams = math.ceil(total / MAX_TEAM_SIZE)
    max_teams = total // MIN_TEAM_SIZE
    if min_teams > max_teams:
        raise ValueError(
            f"Cannot partition {total} consultants into teams of "
            f"{MIN_TEAM_SIZE}-{MAX_TEAM_SIZE} members"
        )

    target_teams = round(total / team_size)
    num_teams = min(max(target_teams, min_teams), max_teams)

    base, remainder = divmod(total, num_teams)
    return [base + 1 if i < remainder else base for i in range(num_teams)]


def assign_teams(
    db: Session, season: Season, rng: random.Random | None = None
) -> list[Team]:
    rng = rng or random.Random()

    existing_teams = db.query(Team).filter(Team.season_id == season.id).all()
    if existing_teams:
        existing_team_ids = [t.id for t in existing_teams]
        db.query(TeamMembership).filter(
            TeamMembership.team_id.in_(existing_team_ids)
        ).delete(synchronize_session=False)
        for team in existing_teams:
            db.delete(team)
        db.flush()

    consultants = _active_consultants(db)
    rng.shuffle(consultants)
    sizes = _team_sizes(len(consultants), season.team_size)

    teams = []
    offset = 0
    for i, size in enumerate(sizes):
        team = Team(season_id=season.id, name=f"Team {i + 1}")
        db.add(team)
        db.flush()
        for consultant in consultants[offset : offset + size]:
            db.add(TeamMembership(team_id=team.id, user_id=consultant.id))
        offset += size
        teams.append(team)

    db.flush()
    return teams


def start_new_season(
    db: Session, name: str, start_date: datetime, end_date: datetime, team_size: int
) -> Season:
    current_active = db.query(Season).filter(Season.status == "active").all()
    for prior_season in current_active:
        prior_season.status = "complete"

    season = create_season(db, name, start_date, end_date, team_size)
    assign_teams(db, season)
    season.status = "active"
    db.flush()
    return season
