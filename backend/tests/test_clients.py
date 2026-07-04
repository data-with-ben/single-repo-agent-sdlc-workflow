from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import Assignment, Client, User


@pytest.fixture()
def db_and_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'clients_test.db'}")
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
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    admin = User(
        display_name="Admin",
        email="admin@example.com",
        roles=["admin"],
        created_at=now,
        status="active",
    )
    consultant = User(
        display_name="Consultant",
        email="consultant@example.com",
        roles=["consultant"],
        created_at=now,
        status="active",
    )
    client_row = Client(name="Acme", status="active", created_at=now)
    session.add_all([admin, consultant, client_row])
    session.commit()
    session.refresh(admin)
    session.refresh(consultant)
    session.refresh(client_row)

    yield session, TestClient(app), admin, consultant, client_row

    app.dependency_overrides.clear()
    session.close()


def test_admin_can_create_and_archive_client(db_and_client):
    _, client, admin, _, _ = db_and_client

    response = client.post(
        "/clients", json={"name": "Globex"}, headers={"X-User-Id": str(admin.id)}
    )
    assert response.status_code == 200
    new_client_id = response.json()["id"]

    response = client.post(
        f"/clients/{new_client_id}/archive", headers={"X-User-Id": str(admin.id)}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_non_admin_cannot_create_or_archive_client(db_and_client):
    _, client, _, consultant, existing_client = db_and_client

    response = client.post(
        "/clients",
        json={"name": "Globex"},
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response.status_code == 403

    response = client.post(
        f"/clients/{existing_client.id}/archive",
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response.status_code == 403


def test_admin_can_assign_and_remove_consultant(db_and_client):
    _, client, admin, consultant, existing_client = db_and_client

    response = client.post(
        f"/clients/{existing_client.id}/assignments",
        json={"consultant_id": consultant.id},
        headers={"X-User-Id": str(admin.id)},
    )
    assert response.status_code == 200

    response = client.get(
        f"/clients/{existing_client.id}/assignments",
        headers={"X-User-Id": str(admin.id)},
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "consultant_id": consultant.id,
            "display_name": "Consultant",
            "start_date": response.json()[0]["start_date"],
        }
    ]

    response = client.delete(
        f"/clients/{existing_client.id}/assignments/{consultant.id}",
        headers={"X-User-Id": str(admin.id)},
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": 1}


def test_non_admin_cannot_assign_or_remove_consultant(db_and_client):
    _, client, _, consultant, existing_client = db_and_client

    response = client.post(
        f"/clients/{existing_client.id}/assignments",
        json={"consultant_id": consultant.id},
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response.status_code == 403

    response = client.delete(
        f"/clients/{existing_client.id}/assignments/{consultant.id}",
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response.status_code == 403


def test_cannot_assign_to_archived_client(db_and_client):
    session, client, admin, consultant, existing_client = db_and_client
    existing_client.status = "archived"
    session.commit()

    response = client.post(
        f"/clients/{existing_client.id}/assignments",
        json={"consultant_id": consultant.id},
        headers={"X-User-Id": str(admin.id)},
    )
    assert response.status_code == 400


def test_assignment_to_unknown_client_or_consultant_is_404(db_and_client):
    _, client, admin, consultant, existing_client = db_and_client

    response = client.post(
        "/clients/999999/assignments",
        json={"consultant_id": consultant.id},
        headers={"X-User-Id": str(admin.id)},
    )
    assert response.status_code == 404

    response = client.post(
        f"/clients/{existing_client.id}/assignments",
        json={"consultant_id": 999999},
        headers={"X-User-Id": str(admin.id)},
    )
    assert response.status_code == 404


def test_duplicate_assignment_is_rejected(db_and_client):
    _, client, admin, consultant, existing_client = db_and_client

    first = client.post(
        f"/clients/{existing_client.id}/assignments",
        json={"consultant_id": consultant.id},
        headers={"X-User-Id": str(admin.id)},
    )
    assert first.status_code == 200

    second = client.post(
        f"/clients/{existing_client.id}/assignments",
        json={"consultant_id": consultant.id},
        headers={"X-User-Id": str(admin.id)},
    )
    assert second.status_code == 409


def test_me_clients_reflects_only_the_calling_users_own_assignments(db_and_client):
    session, client, admin, consultant, existing_client = db_and_client
    session.add(
        Assignment(
            consultant_id=consultant.id,
            client_id=existing_client.id,
            start_date=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    session.commit()

    response = client.get(
        "/me/clients", headers={"X-User-Id": str(consultant.id)}
    )
    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [existing_client.id]

    response = client.get("/me/clients", headers={"X-User-Id": str(admin.id)})
    assert response.status_code == 200
    assert response.json() == []
