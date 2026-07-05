from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Holding, Season, Team, TeamMembership, User
from app.notifications import (
    NUDGE_MESSAGE,
    is_nudge_eligible,
    list_notifications,
    send_nudge,
)

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'notifications_test.db'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


_email_counter = iter(range(1_000_000))


def _make_user(db_session) -> User:
    user = User(
        display_name=f"User {next(_email_counter)}",
        email=f"user{next(_email_counter)}@example.com",
        roles=["consultant"],
        created_at=datetime(2020, 1, 1),
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestEligibilityViaHolding:
    def test_holding_shares_makes_a_sender_eligible(self, db_session):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(
            Holding(user_id=sender.id, consultant_id=consultant.id, shares=5)
        )
        db_session.commit()

        assert is_nudge_eligible(db_session, sender.id, consultant.id) is True

    def test_zero_shares_does_not_make_a_sender_eligible(self, db_session):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(
            Holding(user_id=sender.id, consultant_id=consultant.id, shares=0)
        )
        db_session.commit()

        assert is_nudge_eligible(db_session, sender.id, consultant.id) is False


class TestEligibilityViaRoster:
    def _make_active_season_with_team(self, db_session, *members):
        season = Season(
            name="S",
            start_date=NOW,
            end_date=NOW + timedelta(days=30),
            status="active",
            team_size=3,
        )
        db_session.add(season)
        db_session.flush()
        team = Team(season_id=season.id, name="T")
        db_session.add(team)
        db_session.flush()
        for member in members:
            db_session.add(TeamMembership(team_id=team.id, user_id=member.id))
        db_session.commit()
        return season, team

    def test_teammates_are_eligible_to_nudge_each_other(self, db_session):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)
        self._make_active_season_with_team(db_session, sender, consultant)

        assert is_nudge_eligible(db_session, sender.id, consultant.id) is True

    def test_different_teams_are_not_eligible(self, db_session):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)
        season = Season(
            name="S",
            start_date=NOW,
            end_date=NOW + timedelta(days=30),
            status="active",
            team_size=3,
        )
        db_session.add(season)
        db_session.flush()
        team_a = Team(season_id=season.id, name="A")
        team_b = Team(season_id=season.id, name="B")
        db_session.add_all([team_a, team_b])
        db_session.flush()
        db_session.add(TeamMembership(team_id=team_a.id, user_id=sender.id))
        db_session.add(TeamMembership(team_id=team_b.id, user_id=consultant.id))
        db_session.commit()

        assert is_nudge_eligible(db_session, sender.id, consultant.id) is False

    def test_no_active_season_means_no_roster_eligibility(self, db_session):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)

        assert is_nudge_eligible(db_session, sender.id, consultant.id) is False

    def test_no_teams_for_sender_means_not_eligible(self, db_session):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)
        self._make_active_season_with_team(db_session, consultant)

        assert is_nudge_eligible(db_session, sender.id, consultant.id) is False


class TestSendNudge:
    def test_not_eligible_sender_is_rejected(self, db_session):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)

        with pytest.raises(ValueError, match="not eligible"):
            send_nudge(db_session, sender.id, consultant.id, NOW)

    def test_eligible_sender_creates_a_notification(self, db_session):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(
            Holding(user_id=sender.id, consultant_id=consultant.id, shares=1)
        )
        db_session.commit()

        notification = send_nudge(db_session, sender.id, consultant.id, NOW)
        db_session.commit()

        assert notification.recipient_id == consultant.id
        assert notification.sender_id == sender.id
        assert notification.read is False

    def test_message_is_always_the_fixed_template_never_time_entry_content(
        self, db_session
    ):
        sender = _make_user(db_session)
        consultant = _make_user(db_session)
        db_session.add(
            Holding(user_id=sender.id, consultant_id=consultant.id, shares=1)
        )
        db_session.commit()

        notification = send_nudge(db_session, sender.id, consultant.id, NOW)

        # AC #3: the message is drawn from a fixed template with no
        # parameters -- there is no code path here that could ever thread
        # TimeEntry.description/actual_hours/planned_hours into it.
        assert notification.message == NUDGE_MESSAGE


class TestListNotifications:
    def test_returns_only_the_recipients_own_notifications_newest_first(
        self, db_session
    ):
        sender = _make_user(db_session)
        recipient = _make_user(db_session)
        other_recipient = _make_user(db_session)
        db_session.add(
            Holding(user_id=sender.id, consultant_id=recipient.id, shares=1)
        )
        db_session.add(
            Holding(user_id=sender.id, consultant_id=other_recipient.id, shares=1)
        )
        db_session.commit()

        send_nudge(db_session, sender.id, recipient.id, NOW - timedelta(days=1))
        db_session.commit()
        send_nudge(db_session, sender.id, recipient.id, NOW)
        db_session.commit()
        send_nudge(db_session, sender.id, other_recipient.id, NOW)
        db_session.commit()

        notifications = list_notifications(db_session, recipient.id)

        assert len(notifications) == 2
        assert notifications[0].created_at >= notifications[1].created_at
        assert all(n.recipient_id == recipient.id for n in notifications)
