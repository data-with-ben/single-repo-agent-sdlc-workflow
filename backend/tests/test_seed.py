import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app import models
from app import seed as seed_module
from app.db import Base


@pytest.fixture()
def seeded_db(tmp_path):
    """Points app.seed at a fresh, isolated SQLite engine for the duration
    of the test, then restores its original SessionLocal afterward.
    """
    db_path = tmp_path / "seed_test.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    test_session_local = sessionmaker(bind=engine)

    original_session_local = seed_module.SessionLocal
    seed_module.SessionLocal = test_session_local
    try:
        yield test_session_local
    finally:
        seed_module.SessionLocal = original_session_local


def _counts(session_local):
    session = session_local()
    try:
        return {
            "clients": session.query(models.Client).count(),
            "users": session.query(models.User).count(),
            "assignments": session.query(models.Assignment).count(),
            "seasons": session.query(models.Season).count(),
            "teams": session.query(models.Team).count(),
            "team_memberships": session.query(models.TeamMembership).count(),
            "wallets": session.query(models.Wallet).count(),
            "time_entries": session.query(models.TimeEntry).count(),
        }
    finally:
        session.close()


def test_seed_produces_expected_data(seeded_db):
    seed_module.seed()
    counts = _counts(seeded_db)

    assert counts["clients"] == 3
    assert counts["users"] == seed_module.NUM_CONSULTANTS + 1  # + manager
    assert counts["seasons"] == 1
    assert counts["team_memberships"] == seed_module.NUM_CONSULTANTS
    assert counts["wallets"] == seed_module.NUM_CONSULTANTS + 1

    session = seeded_db()
    try:
        season = session.query(models.Season).one()
        assert season.status == "active"

        player_manager = (
            session.query(models.User)
            .filter(models.User.email == "riley.playermanager@example.com")
            .one()
        )
        for wallet in session.query(models.Wallet).all():
            if wallet.user_id == player_manager.id:
                # Debited by the demo trades seeded below, giving the
                # Portfolio screen (task-31) a real, non-empty holding to
                # render in a freshly seeded environment.
                assert wallet.balance < seed_module.STARTING_BALANCE
            else:
                assert wallet.balance == seed_module.STARTING_BALANCE

        held = session.query(models.Holding).filter(models.Holding.shares > 0).count()
        assert held == 2
    finally:
        session.close()


def test_seed_covers_all_punctuality_profiles(seeded_db):
    """AC #2: consultants have varied, clearly distinguishable punctuality
    profiles -- verify all three profile categories are represented, not
    just a single before/after data point.
    """
    seed_module.seed()

    session = seeded_db()
    try:
        all_users = session.query(models.User).order_by(models.User.id).all()
        consultants = [u for u in all_users if "consultant" in u.roles]

        profile_counts = {profile: 0 for profile in seed_module.PUNCTUALITY_PROFILES}
        for consultant in consultants:
            entries = (
                session.query(models.TimeEntry)
                .filter_by(consultant_id=consultant.id)
                .all()
            )
            assert len(entries) == seed_module.WORKDAYS_SEEDED

            projected_hours = [e.projected_at.hour for e in entries]
            cutoff = seed_module.PROJECT_BY_HOUR
            all_before_11 = all(h < cutoff for h in projected_hours)
            all_after_11 = all(h >= cutoff for h in projected_hours)
            if all_before_11:
                profile_counts["always-on-time"] += 1
            elif all_after_11:
                profile_counts["chronic-late"] += 1
            else:
                profile_counts["streaky"] += 1

        for profile, count in profile_counts.items():
            assert count > 0, f"no consultant matched the '{profile}' profile pattern"
    finally:
        session.close()


def test_seed_is_idempotent(seeded_db):
    """AC #3: re-running the seed script resets prior data rather than
    accumulating duplicates -- row counts must be identical run to run.
    """
    seed_module.seed()
    first_counts = _counts(seeded_db)

    seed_module.seed()
    second_counts = _counts(seeded_db)

    assert first_counts == second_counts
