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
