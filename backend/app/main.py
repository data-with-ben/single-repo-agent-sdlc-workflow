from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

app = FastAPI(title="Backend API")


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
