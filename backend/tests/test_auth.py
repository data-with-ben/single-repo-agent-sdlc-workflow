from datetime import datetime, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth import get_current_user, require_role
from app.db import Base, get_db
from app.models import User


@pytest.fixture()
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'auth_test.db'}")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)

    session = TestSessionLocal()
    try:
        yield session, TestSessionLocal
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    _, TestSessionLocal = db_session

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # A minimal test-only app exercising the two dependencies via real HTTP
    # requests. Kept local to this test file -- app/main.py has no reason
    # to carry endpoints that exist only to test the dependencies.
    test_app = FastAPI()

    @test_app.get("/whoami")
    def whoami(user: User = Depends(get_current_user)):
        return {"id": user.id, "display_name": user.display_name}

    @test_app.get("/admin-only")
    def admin_only(user: User = Depends(require_role("admin"))):
        return {"id": user.id}

    test_app.dependency_overrides[get_db] = override_get_db
    return TestClient(test_app)


def _create_user(session: Session, roles: list[str]) -> User:
    user = User(
        display_name="Test User",
        email=f"test-{'-'.join(roles) or 'none'}@example.com",
        roles=roles,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        status="active",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_get_current_user_rejects_missing_header(client):
    response = client.get("/whoami")
    assert response.status_code == 401


def test_get_current_user_rejects_unknown_user(client):
    response = client.get("/whoami", headers={"X-User-Id": "999999"})
    assert response.status_code == 401


def test_get_current_user_rejects_non_numeric_header(client):
    response = client.get("/whoami", headers={"X-User-Id": "not-a-number"})
    assert response.status_code == 401


def test_get_current_user_accepts_valid_header(client, db_session):
    session, _ = db_session
    user = _create_user(session, roles=["consultant"])

    response = client.get("/whoami", headers={"X-User-Id": str(user.id)})
    assert response.status_code == 200
    assert response.json() == {"id": user.id, "display_name": "Test User"}


def test_require_role_rejects_insufficient_role(client, db_session):
    session, _ = db_session
    user = _create_user(session, roles=["consultant"])

    response = client.get("/admin-only", headers={"X-User-Id": str(user.id)})
    assert response.status_code == 403


def test_require_role_accepts_sufficient_role(client, db_session):
    session, _ = db_session
    user = _create_user(session, roles=["admin"])

    response = client.get("/admin-only", headers={"X-User-Id": str(user.id)})
    assert response.status_code == 200
    assert response.json() == {"id": user.id}
