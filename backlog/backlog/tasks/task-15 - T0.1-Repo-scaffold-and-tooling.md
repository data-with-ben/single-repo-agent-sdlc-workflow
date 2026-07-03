---
id: TASK-15
title: T0.1 Repo scaffold and tooling
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:24'
updated_date: '2026-07-03 20:32'
labels:
  - foundation
dependencies: []
modified_files:
  - README.md
  - backend/README.md
  - backend/app/main.py
  - backend/pyproject.toml
  - backend/tests/test_app.py
  - frontend/README.md
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/eslint.config.js
  - frontend/src/App.tsx
  - frontend/src/App.test.tsx
  - .github/workflows/ci.yml
  - backlog/backlog/tasks/task-15 - T0.1-Repo-scaffold-and-tooling.md
priority: high
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Set up the project skeleton, chosen stack, linting, test runner, and CI hook for the Fantasy Timesheets app.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A hello-world route/app runs
- [x] #2 The test command runs and passes an example test
- [x] #3 Lint passes
- [x] #4 README documents how to run and test the project
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Backend hello-world route: add a GET / route to backend/app/main.py returning a small JSON message payload; add a pytest case in backend/tests/test_app.py asserting the route returns 200 and the expected body. Verifies AC #1 (backend half) and feeds AC #2's example test.
2. Frontend hello-world render: update frontend/src/App.tsx to render visible hello-world text inside the existing main element; update frontend/src/App.test.tsx to assert the text is present, keeping the existing main-presence check. Verifies AC #1 (frontend half) and feeds AC #2's example test.
3. Frontend lint: add ESLint with the TypeScript + React + React Hooks plugin set as devDependencies, add an eslint.config.js consistent with the existing strict tsconfig, and add a lint script to frontend/package.json. Run it once locally to confirm a clean pass on current source. Verifies AC #3 (frontend half).
4. Backend lint: add ruff as a dev dependency in backend/pyproject.toml's dev optional-dependencies, add a tool.ruff config section, and document the invocation in backend/README.md. Run it once locally to confirm a clean pass on current source. Verifies AC #3 (backend half).
5. CI hook: add .github/workflows/ci.yml with two jobs, frontend and backend, on push and pull_request: frontend job runs npm ci, the lint script, and npm test in frontend/; backend job sets up Python 3.11+, installs the dev extras, runs ruff check then pytest. E2E is intentionally excluded from this CI hook since it needs both live servers and is out of scope for a repo-scaffold task -- noted explicitly as a scope decision, not an oversight. Verifies AC #2 via CI and AC #4's CI-hook requirement.
6. README updates: extend the root README.md with a Running the App section covering dev server commands for frontend and backend, and a Running Tests and Lint section covering all three areas -- frontend, backend, and e2e. Verifies AC #4.
7. Verification pass: run frontend tests, frontend lint, backend tests, backend lint, and confirm the new CI workflow YAML is syntactically valid, before handing off to the unit-tests step.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (3 warning(s), 1 minor)

Warning: task-1 (still active, To Do, unflagged) plans a /health backend route and a frontend status display, touching the same two files this plan modifies (backend/app/main.py, frontend/src/App.tsx). Task-1's own description states the backend 'currently has zero routes' and the frontend 'currently renders an empty main element' -- both will be false once task-15 lands. Not blocking task-15, but task-1's implementer must treat that description text as stale and build on top of task-15's hello-world route/text rather than assuming a blank slate.

Warning: step 5 (CI hook) is not tied to any of the four numbered ACs -- it is justified only by the task description's prose ('...and CI hook'). verify-ac should treat the CI workflow as description-driven scope, not stretch an existing AC to cover it, and merge-guard should expect .github/workflows/ci.yml as an intentional addition.

Warning: the plan does not pin an ESLint major version. Flat config (eslint.config.js) requires ESLint 9.x; confirm during implementation that the chosen eslint, typescript-eslint, and eslint-plugin-react-hooks versions are mutually compatible before locking them into package.json -- unverified until installed.

Minor: ruff check . (step 4) should explicitly exclude backend/.venv (and any build artifacts) so lint doesn't run against installed dependencies.

IMPLEMENTATION NOTES

What was implemented:

- Backend: added GET / route to backend/app/main.py returning a hello-world JSON message; added a pytest case asserting status 200 and body.

- Frontend: App.tsx now renders an h1 heading "Hello, Fantasy Timesheets" inside the existing main element; App.test.tsx adds a matching assertion and an afterEach(cleanup) to prevent cross-test DOM leakage now that the file has two tests.

- Frontend lint: added ESLint (flat config) with typescript-eslint, eslint-plugin-react-hooks, and eslint-plugin-react-refresh via npm install (versions resolved by npm, not hand-pinned); added frontend/eslint.config.js and a lint script.

- Backend lint: added ruff to dev extras; added a tool.ruff config excluding .venv and selecting E, F, I rule sets; documented ruff check . in backend/README.md.

- CI: added .github/workflows/ci.yml with a frontend job (npm ci, lint, test) and a backend job (pip install, ruff check, pytest), both on push and pull_request. E2E intentionally excluded, since it needs live servers.

- Docs: root README.md gained Running the App and Running Tests and Lint sections covering frontend, backend, and e2e.

Key technical decisions:

- Let npm resolve ESLint and plugin versions instead of hand-picking numbers, per a hostile-plan-review warning about unverified version compatibility.

- Scoped ruff to exclude .venv explicitly, per a hostile-plan-review minor finding.

- CI covers frontend and backend only, not e2e -- e2e requires two live servers and isn't needed to satisfy any of this task's four ACs.

Integration points:

- New dev dependencies: eslint, eslint-js, typescript-eslint, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals (frontend); ruff (backend).

- No runtime dependencies changed; no config changes needed outside the two package manifests and the new CI workflow.

Testing coverage:

- Backend: pytest, 2 of 2 passed (existing app-exists test plus new hello-world route test).

- Frontend: vitest, 2 of 2 passed (existing main-render test plus new heading test).

- Lint: eslint and ruff both clean.

- E2E: skipped -- no e2e tests exist yet and none are required by this task's ACs.

Future considerations:

- task-1 (still To Do, unflagged) will also touch backend/app/main.py and frontend/src/App.tsx to add a health route and status display; its description text is now stale and its implementer should build on top of this task's changes rather than assuming a blank slate.

- The hello-world route and heading are placeholder scaffolding; later tasks (T1.1+) will replace them with real routes/screens.

CODE REVIEW: Approved with 2 minor suggestions

- Fixed inline: frontend/README.md was missing a Lint section that backend/README.md had; added for symmetry (no re-test needed, doc-only).

- Minor, no action needed: CI pins Node 20 for the frontend job while local dev/testing used Node 24; both are compatible with Vite 6 (requires Node 18+), just noting the version gap for awareness.

SELF-IMPROVEMENT: setup-worktree's bootstrap step (Step 6) has no recovery path when a required system toolchain (node/npm, python3) is missing entirely from the host -- it only documents 'emit WORKTREE_BLOCKED and stop' for install failures, which conflates 'dependency install failed' (needs human debugging) with 'the interpreter itself is not installed' (needs one install command and then bootstrap can proceed normally). In this run, node/npm and python were both missing from a fresh machine; the workflow coordinator improvised by pausing to ask the user whether to install them via winget, which is not a documented gate anywhere in the workflow. Recommend: setup-worktree should explicitly check for node/npm and python3 (or whatever interpreters the repo's package.json/pyproject.toml require) before attempting npm ci / pip install, and if missing, ask the user to approve an install command (winget/apt/brew as appropriate) rather than emitting WORKTREE_BLOCKED outright -- since this is typically a one-command fix, not a task-level blocker.
<!-- SECTION:NOTES:END -->
