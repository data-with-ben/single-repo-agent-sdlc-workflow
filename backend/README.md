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
