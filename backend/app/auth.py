"""Dev-mode identity: the caller is whoever the X-User-Id header names.

This is a stand-in for real authentication, appropriate for a local/demo
scale app -- there is no login/session flow anywhere in SPEC.md. It can be
swapped for real auth later without changing the domain model, since it
resolves to the same User rows either way.
"""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User


def get_current_user(
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> User:
    # x_user_id is read as a plain string (not int) and validated manually --
    # if it were typed as `int`, FastAPI would reject a missing/malformed
    # header with 422 automatically, but AC #1 requires 401 for that case.
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    try:
        user_id = int(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=401, detail="Invalid X-User-Id header"
        ) from None

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def require_role(role: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if role not in user.roles:
            raise HTTPException(status_code=403, detail=f"Requires role: {role}")
        return user

    return dependency
