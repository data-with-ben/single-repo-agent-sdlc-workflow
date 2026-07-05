"""Seed script for local development and testing.

Populates clients, consultants (with varied punctuality profiles), an
active season with teams, and wallets. Run after migrations are applied
(`alembic upgrade head`); this script only inserts rows, it never touches
the schema.

"Empty database" in this module's context means a freshly migrated
database with no rows yet -- not a database missing tables.

Idempotent by reset: every run deletes all seed-managed rows (in
foreign-key-safe order) before inserting fresh ones, so re-running never
produces duplicates or drifts from a clean baseline.

Usage:
    python -m app.seed
"""

import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.game_scheduling import schedule_season_games
from app.models import (
    Assignment,
    Client,
    Dividend,
    Game,
    ObjectiveResult,
    Season,
    Team,
    TeamMembership,
    TimeEntry,
    User,
    Wallet,
)
from app.reveal import reveal_game_date

SEED_RANDOM_SEED = 42

STARTING_BALANCE = 100.0
NUM_CONSULTANTS = 15
TEAM_SIZE_TARGET = 4
WORKDAYS_SEEDED = 5

# Reference threshold from SPEC.md Section 6, applied directly in UTC here.
# Proper per-user local-zone evaluation is deferred to task-22's objective
# engine; this script only needs visibly varied timestamp patterns.
PROJECT_BY_HOUR = 11

PUNCTUALITY_PROFILES = ["always-on-time", "chronic-late", "streaky"]

# Tables to reset, children before parents (FK-safe order).
SEED_MANAGED_MODELS = [
    Dividend,
    ObjectiveResult,
    Game,
    TimeEntry,
    TeamMembership,
    Team,
    Season,
    Assignment,
    Wallet,
    User,
    Client,
]


def _reset(session: Session) -> None:
    for model in SEED_MANAGED_MODELS:
        session.query(model).delete()
    session.commit()


def _last_n_workdays(n: int, from_date: datetime) -> list[datetime]:
    days: list[datetime] = []
    cursor = from_date
    while len(days) < n:
        cursor -= timedelta(days=1)
        if cursor.weekday() < 5:  # Mon-Fri
            days.append(cursor)
    return list(reversed(days))


def _seed_time_entry_for_profile(
    profile: str, work_date: datetime, day_index: int
) -> dict:
    """Returns projected_at/logged_at/updated_at for one work day, shaped by
    the consultant's punctuality profile.
    """
    base = work_date.replace(hour=0, minute=0, second=0, microsecond=0)

    if profile == "always-on-time":
        projected_at = base.replace(hour=9, minute=30)
        logged_at = base.replace(hour=16, minute=0)
        updated_at = base.replace(hour=16, minute=30)
    elif profile == "chronic-late":
        projected_at = base.replace(hour=13, minute=0)
        logged_at = base + timedelta(days=1, hours=10)  # next day
        updated_at = None
    else:  # streaky: alternates on-time and late by day
        on_time_day = day_index % 2 == 0
        if on_time_day:
            projected_at = base.replace(hour=10, minute=0)
            logged_at = base.replace(hour=15, minute=30)
            updated_at = base.replace(hour=15, minute=45)
        else:
            projected_at = base.replace(hour=12, minute=30)
            logged_at = base.replace(hour=17, minute=0)
            updated_at = None

    return {
        "projected_at": projected_at,
        "logged_at": logged_at,
        "updated_at": updated_at,
    }


def seed() -> None:
    # Fixed seed so every run (and re-run) produces byte-identical data --
    # a stronger, simpler idempotency guarantee than merely fixed row counts.
    random.seed(SEED_RANDOM_SEED)

    session = SessionLocal()
    try:
        _reset(session)

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        clients = [
            Client(name=name, status="active", created_at=now)
            for name in ["Acme Corp", "Globex", "Initech"]
        ]
        session.add_all(clients)
        session.flush()

        manager = User(
            display_name="Morgan Manager",
            email="morgan.manager@example.com",
            roles=["admin"],
            created_at=now,
            status="active",
        )
        # A dual-role user, matching SPEC.md Section 2: a manager "may also
        # be consultant and holder".
        player_manager = User(
            display_name="Riley Player-Manager",
            email="riley.playermanager@example.com",
            roles=["admin", "consultant"],
            created_at=now,
            status="active",
        )
        session.add_all([manager, player_manager])
        session.flush()

        consultants: list[User] = [player_manager]
        for i in range(NUM_CONSULTANTS - 1):
            consultants.append(
                User(
                    display_name=f"Consultant {i + 1}",
                    email=f"consultant{i + 1}@example.com",
                    roles=["consultant"],
                    created_at=now,
                    status="active",
                )
            )
        session.add_all(consultants[1:])
        session.flush()

        # Assign each consultant to 1-2 clients.
        for consultant in consultants:
            for client in random.sample(clients, k=random.choice([1, 2])):
                session.add(
                    Assignment(
                        consultant_id=consultant.id,
                        client_id=client.id,
                        start_date=now,
                    )
                )
        session.flush()

        # Computed before the season so its start_date can cover the past
        # workdays TimeEntry rows are seeded for below -- schedule_season_games
        # only generates games from start_date forward, and reveal_game_date
        # needs an actual Game on one of those days to reveal.
        work_days = _last_n_workdays(WORKDAYS_SEEDED, now)

        season = Season(
            name="Season 1",
            start_date=work_days[0],
            end_date=now + timedelta(weeks=4),
            status="active",
            team_size=TEAM_SIZE_TARGET,
        )
        session.add(season)
        session.flush()

        shuffled = consultants[:]
        random.shuffle(shuffled)
        chunks: list[list[User]] = []
        for i in range(0, len(shuffled), TEAM_SIZE_TARGET):
            chunk = shuffled[i : i + TEAM_SIZE_TARGET]
            if len(chunk) < 3 and chunks:
                # fold a too-small trailing chunk into the last team so
                # every team stays within the 3-5 target range
                chunks[-1].extend(chunk)
            else:
                chunks.append(chunk)

        for idx, chunk in enumerate(chunks):
            team = Team(season_id=season.id, name=f"Team {idx + 1}")
            session.add(team)
            session.flush()
            for member in chunk:
                session.add(TeamMembership(team_id=team.id, user_id=member.id))
        session.flush()

        # Wallets for every user (manager, player-manager, consultants) with
        # a starting balance; no Holdings ("empty portfolios").
        for user in [manager, *consultants]:
            session.add(Wallet(user_id=user.id, balance=STARTING_BALANCE))
        session.flush()

        # Assign punctuality profiles round-robin so all three are
        # represented, then seed the last N workdays of TimeEntry rows.
        for idx, consultant in enumerate(consultants):
            profile = PUNCTUALITY_PROFILES[idx % len(PUNCTUALITY_PROFILES)]
            assignment = (
                session.query(Assignment)
                .filter_by(consultant_id=consultant.id)
                .first()
            )
            for day_index, work_date in enumerate(work_days):
                times = _seed_time_entry_for_profile(profile, work_date, day_index)
                state = "updated" if times["updated_at"] else "logged"
                session.add(
                    TimeEntry(
                        consultant_id=consultant.id,
                        work_date=work_date,
                        client_id=assignment.client_id,
                        planned_hours=8,
                        actual_hours=8,
                        description="Worked on client deliverables.",
                        projected_at=times["projected_at"],
                        logged_at=times["logged_at"],
                        updated_at=times["updated_at"],
                        first_submitted_at=times["projected_at"],
                        state=state,
                    )
                )
        session.flush()

        # Schedule the season's round-robin games (covering the seeded
        # workdays through the rest of the season) and reveal the most
        # recent seeded workday, so the scoreboard has real, visible data
        # in the dev environment -- without this, task-27's UI would have
        # nothing to render against a freshly seeded database.
        schedule_season_games(session, season)
        session.flush()
        reveal_game_date(session, work_days[-1].date())

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed()
