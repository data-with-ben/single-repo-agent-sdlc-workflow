from datetime import date, datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.box_score import box_score_for_game, game_summary
from app.db import get_db
from app.models import Assignment, Client, Game, ObjectiveResult, Team, TimeEntry, User
from app.portfolio import exchange_listing, portfolio_summary
from app.timeentry import IllegalTransitionError
from app.timeentry import eod_update as apply_eod_update
from app.timeentry import log as apply_log
from app.timeentry import project as apply_project
from app.trading import execute_buy, execute_sell

app = FastAPI(title="Backend API")

# Vite's dev server runs on :5173 by default; if that port is already
# occupied and Vite auto-increments, this list needs updating too.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class CreateClientRequest(BaseModel):
    name: str


class CreateAssignmentRequest(BaseModel):
    consultant_id: int


class ProjectRequest(BaseModel):
    client_id: int
    work_date: date
    planned_hours: float
    consultant_id: int | None = None


class LogRequest(BaseModel):
    client_id: int
    work_date: date
    actual_hours: float
    consultant_id: int | None = None


class EodUpdateRequest(BaseModel):
    client_id: int
    work_date: date
    description: str
    consultant_id: int | None = None


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


def _resolve_target_consultant_id(
    current_user: User, requested_consultant_id: int | None
) -> int:
    # No existing "admin-or-self" precedent to reuse (task-18 only has
    # admin-only endpoints and a separate self-filtered /me/clients) --
    # this is new authorization logic.
    if requested_consultant_id is None or requested_consultant_id == current_user.id:
        return current_user.id
    if "admin" not in current_user.roles:
        raise HTTPException(
            status_code=403,
            detail="Only an admin can submit a time entry on behalf of another user",
        )
    return requested_consultant_id


def _require_assignment(db: Session, consultant_id: int, client_id: int) -> None:
    assignment = (
        db.query(Assignment)
        .filter_by(consultant_id=consultant_id, client_id=client_id)
        .first()
    )
    if assignment is None:
        raise HTTPException(
            status_code=403,
            detail="Consultant is not assigned to this client",
        )


def _find_or_create_entry(
    db: Session, consultant_id: int, client_id: int, work_date: date
) -> TimeEntry:
    work_date_dt = datetime.combine(work_date, datetime.min.time())
    entry = (
        db.query(TimeEntry)
        .filter_by(
            consultant_id=consultant_id, client_id=client_id, work_date=work_date_dt
        )
        .first()
    )
    if entry is None:
        entry = TimeEntry(
            consultant_id=consultant_id,
            client_id=client_id,
            work_date=work_date_dt,
            state="empty",
        )
        db.add(entry)
        db.flush()
    return entry


def _serialize_entry(entry: TimeEntry) -> dict:
    return {
        "id": entry.id,
        "consultant_id": entry.consultant_id,
        "client_id": entry.client_id,
        "work_date": entry.work_date.date().isoformat(),
        "planned_hours": entry.planned_hours,
        "actual_hours": entry.actual_hours,
        "description": entry.description,
        "projected_at": (
            entry.projected_at.isoformat() + "Z" if entry.projected_at else None
        ),
        "logged_at": entry.logged_at.isoformat() + "Z" if entry.logged_at else None,
        "updated_at": entry.updated_at.isoformat() + "Z" if entry.updated_at else None,
        "first_submitted_at": (
            entry.first_submitted_at.isoformat() + "Z"
            if entry.first_submitted_at
            else None
        ),
        "state": entry.state,
    }


@app.post("/time-entries/project")
def project_time_entry(
    body: ProjectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    consultant_id = _resolve_target_consultant_id(user, body.consultant_id)
    _require_assignment(db, consultant_id, body.client_id)
    entry = _find_or_create_entry(db, consultant_id, body.client_id, body.work_date)
    try:
        apply_project(
            entry,
            body.planned_hours,
            body.client_id,
            datetime.now(timezone.utc).replace(tzinfo=None),
        )
    except IllegalTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=exc.message) from exc
    db.commit()
    return _serialize_entry(entry)


@app.post("/time-entries/log")
def log_time_entry(
    body: LogRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    consultant_id = _resolve_target_consultant_id(user, body.consultant_id)
    _require_assignment(db, consultant_id, body.client_id)
    entry = _find_or_create_entry(db, consultant_id, body.client_id, body.work_date)
    apply_log(entry, body.actual_hours, datetime.now(timezone.utc).replace(tzinfo=None))
    db.commit()
    return _serialize_entry(entry)


@app.post("/time-entries/eod-update")
def eod_update_time_entry(
    body: EodUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    consultant_id = _resolve_target_consultant_id(user, body.consultant_id)
    _require_assignment(db, consultant_id, body.client_id)
    entry = _find_or_create_entry(db, consultant_id, body.client_id, body.work_date)
    apply_eod_update(
        entry, body.description, datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.commit()
    return _serialize_entry(entry)


def _team_names_for(db: Session, team_ids: set[int]) -> dict[int, str]:
    teams = db.query(Team).filter(Team.id.in_(team_ids)).all()
    return {t.id: t.name for t in teams}


@app.get("/games")
def list_games(
    work_date: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    # Matches wireframe 4 (games-view.png): "today's" slate is shown
    # alongside the most recently revealed game (labeled "Final ·
    # yesterday" there), not just an exact single-date match -- a
    # single-date filter would show nothing on a weekend/off day with no
    # scheduled games of its own, hiding the last real result. A 5-day
    # trailing window reliably reaches back to the last workday regardless
    # of where in the week "today" falls.
    target_date = work_date or datetime.now(timezone.utc).date()
    end = datetime(target_date.year, target_date.month, target_date.day) + timedelta(
        days=1
    )
    start = end - timedelta(days=5)

    games = (
        db.query(Game).filter(Game.game_date >= start, Game.game_date < end).all()
    )
    team_names = _team_names_for(
        db, {g.home_team_id for g in games} | {g.away_team_id for g in games}
    )
    is_admin = "admin" in user.roles

    return [
        game_summary(
            game, team_names[game.home_team_id], team_names[game.away_team_id], is_admin
        )
        for game in games
    ]


def _get_game_or_404(db: Session, game_id: int) -> Game:
    game = db.get(Game, game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@app.get("/games/{game_id}/box-score")
def get_box_score(
    game_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    game = _get_game_or_404(db, game_id)
    is_admin = "admin" in user.roles
    if not game.revealed and not is_admin:
        raise HTTPException(status_code=403, detail="Scores are hidden until reveal")

    objective_results = (
        db.query(ObjectiveResult).filter(ObjectiveResult.game_id == game_id).all()
    )
    team_names = _team_names_for(db, {game.home_team_id, game.away_team_id})
    consultant_ids = {r.consultant_id for r in objective_results}
    display_names = {
        u.id: u.display_name
        for u in db.query(User).filter(User.id.in_(consultant_ids)).all()
    }

    box = box_score_for_game(
        game,
        objective_results,
        team_names[game.home_team_id],
        team_names[game.away_team_id],
        display_names,
    )
    return {
        "game_id": box.game_id,
        "home": {
            "team_id": box.home.team_id,
            "team_name": box.home.team_name,
            "normalized_score": box.home.normalized_score,
            "team_bonus_applied": box.home.team_bonus_applied,
            "players": [vars(p) for p in box.home.players],
        },
        "away": {
            "team_id": box.away.team_id,
            "team_name": box.away.team_name,
            "normalized_score": box.away.normalized_score,
            "team_bonus_applied": box.away.team_bonus_applied,
            "players": [vars(p) for p in box.away.players],
        },
        "star_of_game_consultant_id": box.star_of_game_consultant_id,
    }


class TradeRequest(BaseModel):
    consultant_id: int
    shares: int


@app.get("/exchange")
def list_exchange(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return [vars(listing) for listing in exchange_listing(db, now)]


@app.get("/me/portfolio")
def get_my_portfolio(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    summary = portfolio_summary(db, user.id, now)
    return {
        "wallet_balance": summary["wallet_balance"],
        "holdings": [vars(h) for h in summary["holdings"]],
        "dividends": [
            {
                "consultant_id": d.consultant_id,
                "game_date": d.game_date.date().isoformat(),
                "reason": d.reason,
                "shares": d.shares,
                "per_share": d.per_share,
                "total": d.total,
            }
            for d in summary["dividends"]
        ],
        "market_movers": [vars(m) for m in summary["market_movers"]],
    }


@app.post("/trade/buy")
def trade_buy(
    body: TradeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        txn = execute_buy(db, user.id, body.consultant_id, body.shares, now)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    db.commit()
    return {
        "id": txn.id,
        "side": txn.side,
        "shares": txn.shares,
        "price_per_share": txn.price_per_share,
        "total": txn.total,
    }


@app.post("/trade/sell")
def trade_sell(
    body: TradeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        txn = execute_sell(db, user.id, body.consultant_id, body.shares, now)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    db.commit()
    return {
        "id": txn.id,
        "side": txn.side,
        "shares": txn.shares,
        "price_per_share": txn.price_per_share,
        "total": txn.total,
    }


@app.get("/me/time-entries")
def list_my_time_entries(
    start: date,
    end: date,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.min.time())
    entries = (
        db.query(TimeEntry)
        .filter(
            TimeEntry.consultant_id == user.id,
            TimeEntry.work_date >= start_dt,
            TimeEntry.work_date <= end_dt,
        )
        .all()
    )
    return [_serialize_entry(e) for e in entries]
