from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import User, Wallet

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_and_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'brackets_endpoint_test.db'}")
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
    users = [
        User(
            display_name=f"User {i}",
            email=f"bracketuser{i}@example.com",
            roles=["consultant"],
            created_at=datetime(2020, 1, 1),
            status="active",
        )
        for i in range(4)
    ]
    session.add_all(users)
    session.flush()
    for u in users:
        session.add(Wallet(user_id=u.id, balance=1000.0))
    session.commit()
    for u in users:
        session.refresh(u)

    yield TestClient(app), users

    app.dependency_overrides.clear()
    session.close()


class TestGetBrackets:
    def test_returns_matchup_shape(self, db_and_client):
        client, users = db_and_client
        week_start = (NOW - timedelta(days=7)).date().isoformat()

        response = client.get(
            "/brackets",
            params={"week_start": week_start},
            headers={"X-User-Id": str(users[0].id)},
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["matchups"]) == 2
        assert body["bye_user_id"] is None
        matchup = body["matchups"][0]
        assert set(matchup.keys()) == {
            "user_a_id",
            "user_a_display_name",
            "user_a_gain",
            "user_b_id",
            "user_b_display_name",
            "user_b_gain",
            "winner_id",
        }
        # No trades this week -> every matchup is a draw.
        assert matchup["winner_id"] is None
