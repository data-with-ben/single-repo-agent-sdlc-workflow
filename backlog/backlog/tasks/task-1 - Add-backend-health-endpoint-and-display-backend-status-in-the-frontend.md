---
id: TASK-1
title: Add backend health endpoint and display backend status in the frontend
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-06-05 14:11'
updated_date: '2026-07-05 01:48'
labels:
  - backend
  - frontend
  - integration
dependencies: []
references:
  - feature/task-1-health-endpoint-status
modified_files:
  - backend/app/main.py
  - backend/tests/test_app.py
  - frontend/src/App.tsx
  - frontend/src/BackendStatus.tsx
  - frontend/src/BackendStatus.test.tsx
  - frontend/src/ClientAdmin.tsx
  - frontend/src/ClientAdmin.test.tsx
  - e2e/playwright.config.ts
  - e2e/tests/health-status.spec.ts
  - >-
    backlog/backlog/tasks/task-1 -
    Add-backend-health-endpoint-and-display-backend-status-in-the-frontend.md
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The frontend currently has no way to know whether the backend is running. We need a health endpoint on the FastAPI backend and a status indicator in the React frontend that consumes it. This is the first end-to-end integration between the two projects and establishes the pattern (HTTP client setup, cross-origin handling, error states) that future features will follow.

Context:
- Backend is FastAPI (backend/, runs on http://localhost:8000 via uvicorn) and currently has zero routes.
- Frontend is React 18 + TypeScript with Vite (frontend/, runs on http://localhost:5173) and currently renders an empty main element.
- The two run on different ports, so cross-origin requests must be handled (CORS middleware on the backend or a Vite dev-server proxy — implementer's choice, document the decision).
- E2E tests (e2e/, Playwright) start the frontend automatically via webServer config but do not start the backend; backend must be started and the frontend must handle an unreachable backend gracefully.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GET /health on the backend returns HTTP 200 with a JSON body containing at minimum a status field with value "ok"
- [x] #2 The frontend fetches the health endpoint on initial page load and displays the backend status visibly on the page
- [x] #3 When the backend is unreachable, the frontend displays a clear unavailable/error state instead of crashing or showing nothing
- [x] #4 The health request from the frontend dev server (localhost:5173) to the backend (localhost:8000) succeeds without CORS errors
- [x] #5 Backend unit tests cover the /health endpoint response (status code and body)
- [x] #6 Frontend unit tests cover both the success state (status displayed) and the failure state (unavailable message displayed)
- [x] #7 E2E tests cover a healthy and unhealthy check
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Backend: add GET /health to app/main.py returning {status: ok} with HTTP 200 (AC #1). Unauthenticated, following the /users endpoint precedent (bootstrap-style route, no get_current_user dependency) since health checks must work before any identity is established.
2. Backend: add fastapi.middleware.cors.CORSMiddleware to the app (ships with fastapi/starlette, no new dependency), allowing the known local dev origins (http://localhost:5173, http://127.0.0.1:5173), all methods, and all headers (covers X-User-Id used by every other authenticated endpoint, not just health) -- this is the implementer's-choice decision the task calls out explicitly (CORS middleware vs Vite proxy). CORS middleware is chosen over a Vite proxy because it fixes the gap for every endpoint app-wide (not just requests proxied through Vite), matches how task-36 already documents this exact gap for the rest of the API, and does not depend on the dev server specifically (a proxy config would need separate handling in production). This addresses AC #4 and incidentally resolves task-36 (Add CORS middleware to backend API) as well, since the middleware is registered once for the whole app, not per-route -- task-36 should be closed as a duplicate once this lands, or kept only if a broader origin/deployment-driven config is wanted later.
3. Backend test (test_app.py, alongside the existing test_read_root_returns_hello_world): assert GET /health returns 200 and {status: ok} (AC #5).
4. Frontend: add src/BackendStatus.tsx, a small component that calls apiFetch(/health) on mount (via useEffect), and renders one of three states: loading (initial), ok (backend healthy -- show the returned status), or unavailable (fetch rejected or non-2xx) (AC #2, #3). fetch() only rejects on network failure, not on non-2xx, so the fetch chain must both catch a rejected promise and check response.ok before treating the result as healthy.
5. Wire BackendStatus into App.tsx above UserSwitcher, since backend availability is the most foundational piece of state -- everything else on the page depends on the backend being reachable.
6. Frontend test (BackendStatus.test.tsx, following ClientAdmin.test.tsx's vi.stubGlobal(fetch) pattern): one test mocks a resolved 200 {status: ok} response and asserts the healthy state renders; another mocks a rejected fetch promise and asserts the unavailable state renders instead of a crash (AC #6).
7. E2E: update e2e/playwright.config.ts webServer from a single frontend entry to an array of two entries -- backend (migrate + seed + uvicorn on port 8000, using a dedicated DATABASE_URL=sqlite:///./e2e_test.db, Python path branched on process.platform for win32 vs posix venv layout) and the existing frontend entry -- so e2e tests are self-contained and don't depend on a developer having the backend already running (the task's own context flags this exact gap). Add e2e/tests/health-status.spec.ts with two tests: (a) healthy case -- navigate to / with the real backend running and assert the healthy status renders; (b) unhealthy case -- use page.route to abort the /health request specifically for that test (simulating an unreachable backend without needing to stop the real server mid-run) and assert the unavailable state renders (AC #7).
8. Verification pass: run backend pytest and ruff, frontend npm test and npm run lint, npx playwright test for e2e, and a direct curl OPTIONS preflight against /health (and one other authenticated endpoint) to confirm the CORS gap found during task-20/task-36 is actually resolved, not just assumed fixed.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (2 warning(s), 1 minor)

- Warning: AC #3's unreachable-backend state must handle more than a rejected fetch() promise -- response.json() can independently throw on a malformed/non-JSON body even when fetch() itself resolves. Wrap the entire fetch -> response.ok check -> .json() chain in one try/catch (or equivalent), not just a rejected-promise catch plus a separate response.ok branch.
- Warning: the CORS origin allowlist in step 2 hardcodes exactly localhost:5173 and 127.0.0.1:5173. This satisfies AC #4 as literally worded, but if Vite's default port is ever occupied and it auto-increments to 5174+ (observed happening in this same project during a manual verification pass on a prior task), the frontend will silently hit the identical CORS failure again. Not blocking since the AC only requires port 5173, but worth a code comment noting the fixed-port assumption.
- Minor: set allow_credentials=False explicitly on CORSMiddleware for clarity, even though it is already the default -- this app has no cookie-based auth (X-User-Id header only), so there is nothing to gain from enabling it and explicit is better than relying on an unstated default.

Plan deviation: e2e run against a real browser (fresh context, no stored currentUserId in localStorage) revealed that ClientAdmin.tsx fetches /clients unconditionally on mount before any user is selected, gets a 401 error body (not an array), and clients.find is not a function throws uncaught -- React has no error boundary, so this crashes and unmounts the ENTIRE app, including BackendStatus, which had already rendered Backend: ok correctly just before the crash. This is a pre-existing bug from task-18, invisible until now because normal usage always has a stored user id from a prior session. It directly blocks AC #2/#3/#7 from being verifiable in a real browser, since the whole page goes blank. Fix: make ClientAdmin.tsx loadClients check response.ok before treating the body as an array, same defensive pattern BackendStatus.tsx already uses -- minimal, does not touch ClientAdmins own feature scope (task-18) beyond this one guard.

IMPLEMENTATION SUMMARY

What was implemented:
- backend/app/main.py: added GET /health returning {status: ok} (AC #1), unauthenticated like /users, since a health check must work before any identity is established. Also registered fastapi.middleware.cors.CORSMiddleware for the whole app (allow_origins=[localhost:5173, 127.0.0.1:5173], allow_methods=*, allow_headers=*, allow_credentials=False) -- chosen over a Vite dev-server proxy because it fixes cross-origin access for every endpoint app-wide, not just requests routed through Vite, and does not depend on the dev server specifically (AC #4).
- backend/tests/test_app.py: added test_health_returns_ok asserting 200 and the exact body (AC #5).
- frontend/src/BackendStatus.tsx (new): calls apiFetch(/health) on mount, renders loading, ok (Backend: ok), or unavailable (Backend unavailable) -- the whole fetch+ok-check+json-parse chain is wrapped in one try/catch so a rejected fetch promise, a non-2xx response, and a malformed JSON body all land in the same unavailable branch (AC #2, #3).
- frontend/src/BackendStatus.test.tsx (new): three tests -- healthy response, rejected fetch, and non-2xx response, all asserting the correct rendered text (AC #6).
- frontend/src/App.tsx: wired BackendStatus above UserSwitcher, as the most foundational piece of page state.
- e2e/playwright.config.ts: changed webServer from a single frontend entry to an array of two -- backend (alembic upgrade + seed + uvicorn on a dedicated e2e_test.db, python path branched on process.platform for win32 vs posix venv layout) and the existing frontend entry -- so e2e tests are self-contained and do not depend on a developer already having the backend running, per the tasks own context note.
- e2e/tests/health-status.spec.ts (new): healthy case navigates with the real backend running; unhealthy case uses page.route to abort the /health request for that test only, simulating an unreachable backend without needing to stop the real server mid-run (AC #7).

Key technical decisions:
- CORS middleware vs Vite proxy: CORS middleware was chosen (see main.py comment) since it is a one-time, app-wide fix rather than a dev-server-only workaround, and it directly resolves the exact gap task-36 was filed for (confirmed via a direct curl OPTIONS preflight against both /health and the authenticated /me/time-entries endpoint -- both now return 200 with the correct Access-Control-Allow-Origin/Headers). Recommend closing task-36 as resolved by this change, or narrowing its scope to a broader/deployment-driven origin config if still wanted.
- allow_origins is a fixed list of exactly localhost:5173 and 127.0.0.1:5173 (the projects documented Vite port), not a wildcard -- flagged during hostile plan review as a real but non-blocking risk: if that port is ever occupied and Vite auto-increments, the CORS allowlist needs updating too. Documented via a code comment in main.py.
- allow_credentials=False set explicitly even though it is the default, since this app has no cookie-based auth (X-User-Id header only) and there is nothing to gain from enabling it.

Plan deviation (logged during implementation, see earlier note): running the new e2e suite in a real browser (fresh context, no stored currentUserId) surfaced a pre-existing bug in ClientAdmin.tsx (from task-18) -- it fetches /clients unconditionally on mount before any user is selected, gets a 401 error body back, and calls .find on it as if it were an array, throwing uncaught. With no error boundary anywhere in the app, this crashed and unmounted the entire React tree, including BackendStatus, which had already rendered Backend: ok correctly moments earlier. This directly blocked AC #2/#3/#7 from being verifiable in a real browser (the whole page went blank), so loadClients in ClientAdmin.tsx was given a minimal fix: check response.ok before treating the body as an array, the same defensive pattern BackendStatus.tsx already uses. This also required updating ClientAdmin.test.tsx's mock fetch to set ok: true (it never had before, an oversight in the original test), and a new regression test (does not crash when /clients returns a non-ok response) was added to ClientAdmin.test.tsx to lock in the fix.

Integration points:
- No new dependencies -- CORSMiddleware ships with fastapi/starlette already listed in pyproject.toml.
- No env-based origin configuration exists yet in this codebase (API_BASE_URL is similarly hardcoded in frontend/src/api.ts) -- the CORS origin list follows that same convention. A future deployment task will need real, environment-driven origin configuration once the app is actually hosted.

Testing coverage:
- Backend: 39 pytest passed (38 existing + 1 new), ruff clean.
- Frontend: 14 vitest passed (10 existing + 1 modified mock fix + 3 new BackendStatus tests + 1 new ClientAdmin regression test), eslint clean.
- E2E: 2 new tests, both passing, results committed under e2e/test-results/.
- Manual verification: started both servers directly and confirmed via curl that OPTIONS preflights against both /health and /me/time-entries return 200 with correct CORS headers -- the exact class of failure found during task-20/task-36 is genuinely resolved, not just assumed fixed.

Future considerations:
- task-36 (Add CORS middleware to backend API) is very likely resolved by this change and should be reviewed/closed rather than duplicated.
- The hardcoded CORS origin list and API_BASE_URL will both need to become environment-driven once a real deployment/hosting strategy is decided (flagged for the upcoming deployment discussion).
- ClientAdmin.tsx still has no error boundary around it or the rest of the app -- the fix here only guards the one fetch path that was actually observed crashing; a broader error-boundary pass is worth considering as this app grows more screens, though that is out of this tasks scope.

CODE REVIEW: Approved with 2 minor suggestions.

No critical or major issues found. Diff is clean, minimal, and matches existing conventions (BackendStatus.tsx follows the same fetch+cleanup-flag pattern as other components; the CORS middleware registration and /health route are simple and correctly placed; the ClientAdmin.tsx plan-deviation fix is a one-line guard, not a rewrite).

Minor, non-blocking:
- .github/workflows/ci.yml does not run e2e tests at all currently (only frontend lint/test and backend ruff/pytest jobs exist) -- pre-existing gap, not introduced by task-1, but worth noting that the new cross-platform webServer command (branched on process.platform) is untested by actual CI since no e2e job exists yet to exercise it on Linux.
- The CORS allow_origins list is a fixed pair of localhost/127.0.0.1:5173 with no environment-driven configuration -- already flagged during hostile plan review and documented via a code comment; carried forward as a known limitation pending the deployment strategy discussion.

Requirements alignment: all 7 ACs verified against real running code (see AC verification and Implementation Notes), no scope creep beyond the one necessary ClientAdmin.tsx fix (logged as a plan deviation). No security issues (ORM/Pydantic throughout, no raw SQL, no XSS risk, CORS origin allowlist is not a wildcard). No unnecessary dependencies (CORSMiddleware ships with fastapi already).

SELF-IMPROVEMENT: .claude/skills/e2e-tests/assets/playwright.config.ts (the canonical template new e2e projects are bootstrapped from) only starts the frontend dev server in its webServer config, never the backend. This is now the second task (task-20, then task-1) where implementing real end-to-end coverage required independently deriving the same fix: change webServer to an array with a second entry that runs alembic upgrade head + app.seed + uvicorn against a dedicated DATABASE_URL, with the python executable path branched on process.platform (.venv/Scripts/python.exe on win32, .venv/bin/python otherwise) since venv layout differs by OS. Recommend baking this into the canonical template (or documenting it directly in e2e-tests/SKILL.md) so future tasks needing real API integration in e2e tests do not have to re-derive it from scratch a third time.

Found and fixed during merge-guard (Step 12): merge-guard.sh used a two-dot git diff (base..HEAD --name-only) to find changed files, which is a raw snapshot comparison between the two tips rather than a diff against the merge-base. When main advances after a feature branch is cut (as happened here: task-36 was marked Done and the e2e template was updated on main while task-1s branch was already in flight), those unrelated files show up as false-positive scope creep even though the feature branch never touched them. Fixed by switching to three-dot notation (base...HEAD), matching the pattern already used correctly in code-review, implementation-notes, and unit-tests SKILL.md. Fixed on main directly (workflow tooling script, not part of task-1s own file scope); the fixed script was invoked from the main checkouts path against the task-1 worktree to verify, rather than bundling the fix into task-1s own branch history.
<!-- SECTION:NOTES:END -->
