from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Season, Team, TeamMembership, User
from app.season import assign_teams, create_season, start_new_season

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'season_test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


_email_counter = iter(range(1_000_000))


def _make_consultants(db_session, count: int, status: str = "active") -> list[User]:
    users = [
        User(
            display_name=f"Consultant {next(_email_counter)}",
            email=f"consultant{next(_email_counter)}@example.com",
            roles=["consultant"],
            created_at=NOW,
            status=status,
        )
        for _ in range(count)
    ]
    db_session.add_all(users)
    db_session.commit()
    return users


def _make_season(db_session, team_size: int = 4) -> Season:
    season = create_season(
        db_session,
        name="Season 1",
        start_date=NOW,
        end_date=NOW + timedelta(days=14),
        team_size=team_size,
    )
    db_session.commit()
    return season


class TestTeamSizeBounds:
    @pytest.mark.parametrize("count", list(range(3, 51)))
    def test_every_team_size_stays_within_bounds_across_a_range_of_n(
        self, db_session, count
    ):
        _make_consultants(db_session, count)
        season = _make_season(db_session)

        teams = assign_teams(db_session, season)
        db_session.commit()

        for team in teams:
            members = (
                db_session.query(TeamMembership)
                .filter(TeamMembership.team_id == team.id)
                .count()
            )
            assert 3 <= members <= 5

    def test_too_few_consultants_raises(self, db_session):
        _make_consultants(db_session, 2)
        season = _make_season(db_session)

        with pytest.raises(ValueError):
            assign_teams(db_session, season)


class TestEveryActiveConsultantPlaced:
    def test_every_active_consultant_appears_on_exactly_one_team(self, db_session):
        consultants = _make_consultants(db_session, 10)
        season = _make_season(db_session)

        assign_teams(db_session, season)
        db_session.commit()

        memberships = db_session.query(TeamMembership).all()
        placed_ids = {m.user_id for m in memberships}
        assert placed_ids == {c.id for c in consultants}
        assert len(memberships) == len(consultants)

    def test_pto_consultant_is_excluded(self, db_session):
        active = _make_consultants(db_session, 4, status="active")
        pto = _make_consultants(db_session, 1, status="pto")
        season = _make_season(db_session, team_size=4)

        assign_teams(db_session, season)
        db_session.commit()

        placed_ids = {m.user_id for m in db_session.query(TeamMembership).all()}
        assert placed_ids == {c.id for c in active}
        assert pto[0].id not in placed_ids

    def test_non_consultant_role_is_excluded(self, db_session):
        _make_consultants(db_session, 3)
        admin_only = User(
            display_name="Admin Only",
            email="admin-only@example.com",
            roles=["admin"],
            created_at=NOW,
            status="active",
        )
        db_session.add(admin_only)
        db_session.commit()
        season = _make_season(db_session, team_size=3)

        assign_teams(db_session, season)
        db_session.commit()

        placed_ids = {m.user_id for m in db_session.query(TeamMembership).all()}
        assert admin_only.id not in placed_ids


class TestReshufflingProducesDifferentTeams:
    def test_two_different_seeds_produce_different_team_compositions(self, db_session):
        import random

        _make_consultants(db_session, 12)
        season = _make_season(db_session)

        assign_teams(db_session, season, rng=random.Random(1))
        db_session.commit()
        first_compositions = {
            team.id: {m.user_id for m in team.members}
            for team in db_session.query(Team).all()
        }

        assign_teams(db_session, season, rng=random.Random(2))
        db_session.commit()
        second_compositions = {
            team.id: {m.user_id for m in team.members}
            for team in db_session.query(Team).all()
        }

        assert first_compositions != second_compositions

    def test_reassigning_replaces_old_teams_rather_than_duplicating(self, db_session):
        _make_consultants(db_session, 8)
        season = _make_season(db_session)

        assign_teams(db_session, season)
        db_session.commit()
        first_team_count = db_session.query(Team).count()

        assign_teams(db_session, season)
        db_session.commit()
        second_team_count = db_session.query(Team).count()

        assert second_team_count == first_team_count


class TestSeasonLifecycle:
    def test_new_season_starts_as_active(self, db_session):
        _make_consultants(db_session, 6)
        season = start_new_season(
            db_session, "Season A", NOW, NOW + timedelta(days=14), 4
        )
        db_session.commit()
        assert season.status == "active"

    def test_starting_a_new_season_completes_the_previously_active_one(
        self, db_session
    ):
        _make_consultants(db_session, 6)
        first = start_new_season(
            db_session, "Season A", NOW, NOW + timedelta(days=14), 4
        )
        db_session.commit()
        first_id = first.id

        start_new_season(
            db_session,
            "Season B",
            NOW + timedelta(days=15),
            NOW + timedelta(days=29),
            4,
        )
        db_session.commit()

        refreshed_first = db_session.get(Season, first_id)
        assert refreshed_first.status == "complete"

    def test_only_one_season_is_active_at_a_time(self, db_session):
        _make_consultants(db_session, 6)
        start_new_season(db_session, "Season A", NOW, NOW + timedelta(days=14), 4)
        db_session.commit()
        start_new_season(
            db_session,
            "Season B",
            NOW + timedelta(days=15),
            NOW + timedelta(days=29),
            4,
        )
        db_session.commit()

        active_seasons = db_session.query(Season).filter_by(status="active").all()
        assert len(active_seasons) == 1


class TestCreateSeasonValidation:
    @pytest.mark.parametrize("team_size", [2, 6])
    def test_team_size_outside_bounds_raises(self, db_session, team_size):
        with pytest.raises(ValueError):
            create_season(
                db_session, "Bad Season", NOW, NOW + timedelta(days=14), team_size
            )
