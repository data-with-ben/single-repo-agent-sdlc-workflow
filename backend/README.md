# Backend

FastAPI backend (Python 3.11+).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```

## Lint

```bash
ruff check .
```

## Database migrations

Uses SQLAlchemy models (`app/models.py`) and Alembic. `DATABASE_URL` env var
overrides the default SQLite file (`sqlite:///./fantasy_timesheets.db`).

```bash
# Apply all migrations to bring the database up to date
alembic upgrade head

# After changing a model, generate a new migration
alembic revision --autogenerate -m "describe the change"
```

See `docs/er-diagram.md` for the current entity-relationship diagram.

## Seed data

Populates clients, ~15 consultants with varied punctuality profiles, an
active season with teams, and starting wallets -- enough to exercise
every planned screen and the nightly reveal job during development.
Run after migrations are applied:

```bash
alembic upgrade head
python -m app.seed
```

Re-running is safe: `seed()` resets all seed-managed tables before
inserting fresh data, using a fixed random seed so every run produces
byte-identical results.
