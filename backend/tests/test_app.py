from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import User

client = TestClient(app)


def test_app_exists():
    assert app.title == "Backend API"


def test_read_root_returns_hello_world():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "hello world"}


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.fixture()
def users_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'users_test.db'}")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)

    session = TestSessionLocal()
    session.add(
        User(
            display_name="Ada",
            email="ada@example.com",
            roles=["consultant"],
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="active",
        )
    )
    session.commit()
    session.close()

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_users_is_unauthenticated_and_returns_seeded_shape(users_client):
    response = users_client.get("/users")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "display_name": "Ada", "roles": ["consultant"]}
    ]
