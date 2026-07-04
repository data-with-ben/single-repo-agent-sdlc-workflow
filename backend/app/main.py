from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models import Assignment, Client, User

app = FastAPI(title="Backend API")


class CreateClientRequest(BaseModel):
    name: str


class CreateAssignmentRequest(BaseModel):
    consultant_id: int


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "hello world"}


@app.get("/users")
def list_users(db: Session = Depends(get_db)) -> list[dict]:
    # Intentionally unauthenticated: this endpoint solves the bootstrap
    # problem for the dev-mode current-user switcher -- a caller needs to
    # see who they can *be* before any X-User-Id identity is established.
    # Endpoints that mutate or expose per-user data must require
    # get_current_user / require_role from app.auth; do not copy this
    # unauthenticated pattern for those.
    users = db.query(User).order_by(User.id).all()
    return [
        {"id": u.id, "display_name": u.display_name, "roles": u.roles}
        for u in users
    ]


@app.get("/clients")
def list_clients(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[dict]:
    clients = db.query(Client).order_by(Client.id).all()
    return [{"id": c.id, "name": c.name, "status": c.status} for c in clients]


@app.post("/clients")
def create_client(
    body: CreateClientRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> dict:
    client = Client(
        name=body.name,
        status="active",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return {"id": client.id, "name": client.name, "status": client.status}


def _get_client_or_404(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.post("/clients/{client_id}/archive")
def archive_client(
    client_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> dict:
    client = _get_client_or_404(db, client_id)
    client.status = "archived"
    db.commit()
    return {"id": client.id, "name": client.name, "status": client.status}


@app.get("/clients/{client_id}/assignments")
def list_client_assignments(
    client_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> list[dict]:
    _get_client_or_404(db, client_id)
    assignments = db.query(Assignment).filter_by(client_id=client_id).all()
    return [
        {
            "consultant_id": a.consultant_id,
            "display_name": db.get(User, a.consultant_id).display_name,
            "start_date": a.start_date.isoformat(),
        }
        for a in assignments
    ]


@app.post("/clients/{client_id}/assignments")
def create_assignment(
    client_id: int,
    body: CreateAssignmentRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> dict:
    client = _get_client_or_404(db, client_id)
    if client.status == "archived":
        raise HTTPException(
            status_code=400, detail="Cannot assign a consultant to an archived client"
        )
    consultant = db.get(User, body.consultant_id)
    if consultant is None:
        raise HTTPException(status_code=404, detail="Consultant not found")

    existing = (
        db.query(Assignment)
        .filter_by(client_id=client_id, consultant_id=body.consultant_id)
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Already assigned")

    assignment = Assignment(
        consultant_id=body.consultant_id,
        client_id=client_id,
        start_date=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(assignment)
    db.commit()
    return {"consultant_id": body.consultant_id, "client_id": client_id}


@app.delete("/clients/{client_id}/assignments/{consultant_id}")
def delete_assignment(
    client_id: int,
    consultant_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> dict:
    # Deletes every matching row -- Assignment has no uniqueness constraint,
    # and create_assignment above prevents duplicates going forward, but
    # this stays safe even if a duplicate somehow exists.
    deleted = (
        db.query(Assignment)
        .filter_by(client_id=client_id, consultant_id=consultant_id)
        .delete()
    )
    db.commit()
    return {"deleted": deleted}


@app.get("/me/clients")
def list_my_clients(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    client_ids = [
        a.client_id
        for a in db.query(Assignment).filter_by(consultant_id=user.id).all()
    ]
    clients = db.query(Client).filter(Client.id.in_(client_ids)).all()
    return [{"id": c.id, "name": c.name, "status": c.status} for c in clients]
