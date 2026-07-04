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
    engine = create_engine(f"sqlite:///{tmp_path / 'timeentry_test.db'}")
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
    other_consultant = User(
        display_name="Other Consultant",
        email="other@example.com",
        roles=["consultant"],
        created_at=now,
        status="active",
    )
    client_row = Client(name="Acme", status="active", created_at=now)
    second_client_row = Client(name="Globex", status="active", created_at=now)
    session.add_all(
        [admin, consultant, other_consultant, client_row, second_client_row]
    )
    session.commit()
    session.refresh(admin)
    session.refresh(consultant)
    session.refresh(other_consultant)
    session.refresh(client_row)
    session.refresh(second_client_row)

    session.add_all(
        [
            Assignment(
                consultant_id=consultant.id, client_id=client_row.id, start_date=now
            ),
            Assignment(
                consultant_id=consultant.id,
                client_id=second_client_row.id,
                start_date=now,
            ),
        ]
    )
    session.commit()

    yield (
        TestClient(app),
        admin,
        consultant,
        other_consultant,
        client_row,
        second_client_row,
    )

    app.dependency_overrides.clear()
    session.close()


def test_consultant_can_project_against_their_own_assignment(db_and_client):
    client, _, consultant, _, acme, _ = db_and_client

    response = client.post(
        "/time-entries/project",
        json={"client_id": acme.id, "work_date": "2026-07-06", "planned_hours": 8},
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "projected"


def test_consultant_cannot_submit_against_an_unassigned_client(db_and_client):
    client, _, _, other_consultant, acme, _ = db_and_client

    response = client.post(
        "/time-entries/project",
        json={"client_id": acme.id, "work_date": "2026-07-06", "planned_hours": 8},
        headers={"X-User-Id": str(other_consultant.id)},
    )
    assert response.status_code == 403


def test_admin_can_submit_on_behalf_of_any_consultant(db_and_client):
    client, admin, consultant, _, acme, _ = db_and_client

    response = client.post(
        "/time-entries/log",
        json={
            "client_id": acme.id,
            "work_date": "2026-07-06",
            "actual_hours": 8,
            "consultant_id": consultant.id,
        },
        headers={"X-User-Id": str(admin.id)},
    )
    assert response.status_code == 200
    assert response.json()["consultant_id"] == consultant.id


def test_consultant_cannot_submit_on_behalf_of_another_consultant(db_and_client):
    client, _, consultant, other_consultant, acme, _ = db_and_client

    response = client.post(
        "/time-entries/project",
        json={
            "client_id": acme.id,
            "work_date": "2026-07-06",
            "planned_hours": 8,
            "consultant_id": other_consultant.id,
        },
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response.status_code == 403


def test_illegal_project_transition_returns_409(db_and_client):
    client, _, consultant, _, acme, _ = db_and_client
    body_base = {"client_id": acme.id, "work_date": "2026-07-06"}

    client.post(
        "/time-entries/log",
        json={**body_base, "actual_hours": 8},
        headers={"X-User-Id": str(consultant.id)},
    )

    response = client.post(
        "/time-entries/project",
        json={**body_base, "planned_hours": 8},
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response.status_code == 409


def test_multiple_entries_per_consultant_and_workdate_across_clients(db_and_client):
    client, _, consultant, _, acme, globex = db_and_client

    response_a = client.post(
        "/time-entries/project",
        json={"client_id": acme.id, "work_date": "2026-07-06", "planned_hours": 4},
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response_a.status_code == 200
    entry_a_id = response_a.json()["id"]

    response_b = client.post(
        "/time-entries/project",
        json={"client_id": globex.id, "work_date": "2026-07-06", "planned_hours": 4},
        headers={"X-User-Id": str(consultant.id)},
    )
    assert response_b.status_code == 200
    entry_b_id = response_b.json()["id"]

    assert entry_a_id != entry_b_id
