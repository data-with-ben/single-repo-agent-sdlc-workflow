# Agent SDLC Workflow

A harness for running an end-to-end software development lifecycle (SDLC) workflow with an autonomous agent. The agent claims backlog tasks, runs intake, plans and implements changes, runs tests and reviews, and closes out work.

## Architecture

This is a mono-repo. All four project areas live as top-level subdirectories:

- **frontend/** — React + TypeScript (Vite, Vitest)
- **backend/** — FastAPI (Python 3.11+)
- **e2e/** — Playwright end-to-end tests
- **backlog/** — Backlog.md CLI-based task store

## Getting Started

1. Clone this repo:
   ```bash
   git clone <repo-url> <project-folder>
   cd <project-folder>
   ```

2. Create subdirectories for any role that doesn't exist yet:
   ```bash
   mkdir -p frontend backend e2e backlog
   ```

3. Initialize the backlog (if starting fresh):
   ```bash
   cd backlog && backlog init && cd ..
   ```

4. Update backlog config.yml with required workflow statuses:
```
statuses: ["To Do", "Intake", "Intake Review", "Plan", "Plan Review", "Code", "AI Code Review", "Human Code Review", "Done"]
``` 

## Workflow

When you want the agent to coordinate a task end-to-end, invoke the `workflow` skill. It runs the full 13-step lifecycle: claim work → intake → plan → implement → test → review → close out. See `CLAUDE.md` and `.claude/skills/workflow/SKILL.md` for details.

## Running the App

**Frontend** (http://localhost:5173):
```bash
cd frontend
npm ci
npm run dev
```

**Backend** (http://localhost:8000):
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # .venv\Scripts\activate on Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Running Tests and Lint

**Frontend:**
```bash
cd frontend
npm test
npm run lint
```

**Backend:**
```bash
cd backend
pytest
ruff check .
```

**End-to-end** (requires both the frontend and backend running):
```bash
cd e2e
npm ci
npm test
```

CI runs the frontend and backend test and lint commands on every push and pull request (`.github/workflows/ci.yml`). E2E tests are not run in CI since they require both live servers.
