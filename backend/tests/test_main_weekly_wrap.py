from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import Holding, User

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_and_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'weekly_wrap_endpoint_test.db'}")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    session = TestSessionLocal()
    sender = User(
        display_name="Sender",
        email="sender@example.com",
        roles=["consultant"],
        created_at=NOW,
        status="active",
    )
    consultant = User(
        display_name="Consultant",
        email="consultant@example.com",
        roles=["consultant"],
        created_at=NOW,
        status="active",
    )
    session.add_all([sender, consultant])
    session.commit()
    session.refresh(sender)
    session.refresh(consultant)

    yield TestClient(app), sender, consultant

    app.dependency_overrides.clear()
    session.close()


class TestGetWeeklyWrap:
    def test_returns_bundled_shape(self, db_and_client):
        client, sender, _consultant = db_and_client
        week_start = (NOW - timedelta(days=7)).date().isoformat()

        response = client.get(
            "/weekly-wrap",
            params={"week_start": week_start},
            headers={"X-User-Id": str(sender.id)},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["team_records"] == []
        # With no game/objective history, every consultant prices flat at
        # the bare BASE fair value -- a 0% swing is still a valid biggest
        # swing (there is at least one consultant to report), matching
        # portfolio.py's market_movers precedent for a quiet period.
        assert body["biggest_market_swing"]["swing_pct"] == 0.0
        assert body["star_performer"] is None


class TestPostNudge:
    def test_not_eligible_sender_gets_400(self, db_and_client):
        client, sender, consultant = db_and_client

        response = client.post(
            "/nudge",
            json={"consultant_id": consultant.id},
            headers={"X-User-Id": str(sender.id)},
        )

        assert response.status_code == 400
        assert "not eligible" in response.json()["detail"]

    def test_eligible_sender_succeeds_and_is_listed_for_the_recipient(
        self, db_and_client
    ):
        client, sender, consultant = db_and_client
        # Held via a direct DB write for test setup speed (holding shares
        # is exercised end-to-end elsewhere; here we only care about the
        # nudge/notification path).
        override = app.dependency_overrides[get_db]
        db = next(override())
        db.add(Holding(user_id=sender.id, consultant_id=consultant.id, shares=1))
        db.commit()

        response = client.post(
            "/nudge",
            json={"consultant_id": consultant.id},
            headers={"X-User-Id": str(sender.id)},
        )
        assert response.status_code == 200

        notifications = client.get(
            "/me/notifications", headers={"X-User-Id": str(consultant.id)}
        ).json()
        assert len(notifications) == 1
        assert notifications[0]["sender_id"] == sender.id
        assert notifications[0]["created_at"].endswith("Z")
