import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import models
from app.db import Base

BACKEND_ROOT = Path(__file__).resolve().parent.parent

ALL_TABLES = {
    "users",
    "clients",
    "assignments",
    "time_entries",
    "seasons",
    "teams",
    "team_memberships",
    "games",
    "objective_results",
    "holdings",
    "transactions",
    "dividends",
    "wallets",
}


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "test.db"


def test_migration_runs_clean_from_empty_database(db_path):
    database_url = f"sqlite:///{db_path}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env={"DATABASE_URL": database_url, **_base_env()},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert ALL_TABLES.issubset(tables)


def _base_env():
    import os

    return dict(os.environ)


@pytest.fixture()
def session(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'unit.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})

    @event.listens_for(Engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_all_entities_exist_with_spec_fields(session):
    now = datetime.now(timezone.utc)

    user = models.User(
        display_name="Ada",
        email="ada@example.com",
        roles=["consultant"],
        created_at=now,
        status="active",
    )
    client = models.Client(name="Acme Co", status="active", created_at=now)
    season = models.Season(
        name="Season 1",
        start_date=now,
        end_date=now,
        status="upcoming",
        team_size=4,
    )
    session.add_all([user, client, season])
    session.flush()

    assignment = models.Assignment(
        consultant_id=user.id, client_id=client.id, start_date=now
    )
    time_entry = models.TimeEntry(
        consultant_id=user.id,
        work_date=now,
        client_id=client.id,
        state="empty",
    )
    team = models.Team(season_id=season.id, name="Team A")
    session.add_all([assignment, time_entry, team])
    session.flush()

    membership = models.TeamMembership(team_id=team.id, user_id=user.id)
    game = models.Game(
        game_date=now,
        season_id=season.id,
        home_team_id=team.id,
        away_team_id=team.id,
        revealed=False,
        state="scheduled",
    )
    session.add_all([membership, game])
    session.flush()

    objective_result = models.ObjectiveResult(
        game_id=game.id,
        game_date=now,
        consultant_id=user.id,
        team_id=team.id,
        points=10,
    )
    holding = models.Holding(user_id=user.id, consultant_id=user.id, shares=5)
    transaction = models.Transaction(
        user_id=user.id,
        consultant_id=user.id,
        side="buy",
        shares=5,
        price_per_share=2.5,
        total=12.5,
        executed_at=now,
    )
    dividend = models.Dividend(
        user_id=user.id,
        consultant_id=user.id,
        game_date=now,
        reason="team_win",
        shares=5,
        per_share=2.0,
        total=10.0,
    )
    wallet = models.Wallet(user_id=user.id, balance=100.0)
    session.add_all([objective_result, holding, transaction, dividend, wallet])
    session.commit()

    assert session.query(models.User).count() == 1
    assert session.get(models.Wallet, user.id).balance == 100.0


def test_foreign_key_violation_is_rejected(session):
    with pytest.raises(IntegrityError):
        session.add(
            models.TimeEntry(
                consultant_id=999999,  # no such user
                work_date=datetime.now(timezone.utc),
                client_id=999999,  # no such client
                state="empty",
            )
        )
        session.commit()
