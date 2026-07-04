---
id: TASK-35
title: Dev-mode current-user identity mechanism
status: Done
assignee:
  - '@agent'
created_date: '2026-07-04 02:35'
updated_date: '2026-07-04 02:56'
labels:
  - backend
  - frontend
  - foundation
dependencies:
  - TASK-16
references:
  - feature/task-35-dev-current-user
modified_files:
  - backend/app/db.py
  - backend/app/auth.py
  - backend/app/main.py
  - backend/tests/test_app.py
  - backend/tests/test_auth.py
  - frontend/src/App.tsx
  - frontend/src/App.test.tsx
  - frontend/src/currentUser.tsx
  - frontend/src/currentUserContext.ts
  - frontend/src/api.ts
  - frontend/src/api.test.ts
  - frontend/src/UserSwitcher.tsx
  - frontend/src/UserSwitcher.test.tsx
  - backlog/backlog/tasks/task-35 - Dev-mode-current-user-identity-mechanism.md
priority: high
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
There is no login/session flow specified anywhere in SPEC.md or the T0-T5 backlog, yet almost every later task needs to know which user is calling: role checks (admin vs consultant) and per-user actions (a consultant's own timesheet, a user's own wallet/portfolio, trades). Rather than build real authentication (out of scope for a local/demo-scale game per SPEC.md's non-goals), add a minimal dev-mode mechanism: the caller is identified by a request header checked against the existing User table (from task-16's data model), with a simple frontend switcher to set it. This is a stand-in that can be swapped for real auth later without changing the domain model.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A FastAPI dependency resolves the current user from a request header (e.g. X-User-Id) against the User table, returning 401 if the header is missing or names a nonexistent user
- [x] #2 Endpoints can require a minimum role (e.g. admin) via this dependency and reject insufficient roles with 403
- [x] #3 The frontend has a current-user switcher (a dropdown of known users) that sets the header on every API request
- [x] #4 Backend and frontend unit tests cover the dependency's allow/deny cases and the switcher setting the header correctly
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Backend: add a get_db() FastAPI dependency generator to app/db.py (yields a Session, closes it after the request) -- needed by any endpoint/dependency that touches the database, and not yet present since prior tasks only used sessions directly in scripts/tests.
2. Backend: add app/auth.py with get_current_user(x_user_id header, db) -> User, raising 401 if the header is missing or names a nonexistent user, and a require_role(role) dependency factory that calls get_current_user and raises 403 if the role isn't in user.roles. Verifies AC #1 and #2.
3. Backend: add GET /users to app/main.py returning id/display_name/roles for every user, unauthenticated -- this is what the frontend switcher needs to populate its dropdown before any identity is set (a real, useful endpoint, not a throwaway demo). Does not itself require current-user, since nothing is known yet at that point.
4. Backend tests (tests/test_auth.py): test get_current_user against a temporary test app/router covering missing header (401), unknown user id (401), and valid header (200 with correct user); test require_role covering insufficient role (403) and sufficient role (200); test GET /users returns seeded-shape data. Verifies AC #1, #2, #4 (backend half).
5. Frontend: add src/currentUser.ts, a small React context holding the selected user id, persisted to localStorage so the choice survives reloads (no new state-management dependency needed).
6. Frontend: add src/api.ts, a fetch wrapper that reads the current user id from context/localStorage and attaches it as the X-User-Id header on every request; all future API calls should go through this wrapper rather than calling fetch directly.
7. Frontend: add src/UserSwitcher.tsx -- fetches GET /users on mount, renders a dropdown, updates the current-user context on change. Wire it into App.tsx above the existing hello-world content. Verifies AC #3.
8. Frontend tests: UserSwitcher renders fetched users and updates the selected user on change (mocking fetch); api.ts attaches the X-User-Id header from the current selection (mocking fetch and asserting the request init). Verifies AC #4 (frontend half).
9. Verification pass: run backend pytest and ruff, frontend npm test and npm run lint, and manually start both servers to confirm switching users in the dropdown actually changes the header sent (checked via browser devtools or a temporary console log) before handing off to unit-tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (2 warning(s), 1 minor)

- Warning: GET /users (step 3) is deliberately unauthenticated to solve the bootstrap problem (you need to know who you can be before any identity exists). Document this explicitly in a code comment so future tasks don't treat 'unauthenticated by default' as the norm for other listing endpoints that should actually be protected.

- Warning: the temporary test app/router used to exercise get_current_user/require_role (step 4) must be defined inside tests/test_auth.py itself, not under app/, so it doesn't become permanent dead surface area.

- Minor: FastAPI will return 422, not 401, if X-User-Id is present but not a valid integer (automatic type-coercion failure) -- AC #1 only requires 401 for missing header or nonexistent user, so this is compliant as written; no fix needed, just worth being aware of.

Plan deviation: get_current_user reads X-User-Id as a plain string and validates it manually, rather than typing the FastAPI Header parameter as int. A typed int Header parameter would make FastAPI auto-reject a missing or non-numeric header with a 422, but AC #1 explicitly requires 401 for a missing header -- manual validation was needed to hit that exact status code.

E2E: skipped -- the UserSwitcher UI change is real, but exercising it end-to-end requires the backend running for GET /users, and Playwright's webServer config only auto-starts the frontend (documented limitation since task-1). Backend and frontend behavior are both already covered by real-request-cycle tests (FastAPI TestClient for auth, React Testing Library for the switcher's DOM interaction and localStorage persistence).

IMPLEMENTATION NOTES

What was implemented:

- Backend: app/db.py gained get_db(), a FastAPI dependency generator yielding a Session and closing it after the request.

- Backend: app/auth.py adds get_current_user (resolves X-User-Id header against the User table, 401 for missing/malformed/unknown) and require_role(role) (403 if the role isn't in user.roles). Both are reusable FastAPI dependencies for any future endpoint.

- Backend: app/main.py gained GET /users (id/display_name/roles for every user), intentionally unauthenticated -- it's what the frontend switcher needs to know who it can become before any identity is set.

- Backend tests: tests/test_auth.py exercises get_current_user and require_role via a small test-only FastAPI app (kept local to the test file, not under app/); tests/test_app.py gained a test for GET /users.

- Frontend: src/currentUserContext.ts (context, localStorage read/write, useCurrentUser hook) and src/currentUser.tsx (CurrentUserProvider component) -- split into two files after ESLint's react-refresh rule flagged mixing component and non-component exports in one file.

- Frontend: src/api.ts, a fetch wrapper attaching X-User-Id from the stored selection; all future API calls should go through this.

- Frontend: src/UserSwitcher.tsx, a dropdown that fetches /users on mount and updates the current-user context on change; wired into App.tsx above the existing hello-world content.

- Frontend tests: api.test.ts (header attachment/omission), UserSwitcher.test.tsx (renders fetched users, persists selection to localStorage); App.test.tsx updated to mock fetch since UserSwitcher now calls it on mount.

Key technical decisions:

- get_current_user reads X-User-Id as a plain string and validates manually (missing -> 401, non-numeric -> 401, unknown user -> 401) rather than typing the FastAPI Header parameter as int, which would have produced an automatic 422 for a missing/malformed header instead of the 401 AC #1 requires. Documented as a plan deviation.

- GET /users is deliberately unauthenticated (bootstrap problem: you need to know who you can be before any identity exists); a code comment explicitly warns against copying this pattern for endpoints that should be protected.

- The test-only FastAPI app in test_auth.py lives entirely in the test file, not under app/, so the dependencies are exercised via real HTTP requests without adding permanent unused business endpoints.

Integration points:

- No new dependencies (frontend or backend).

- Future tasks (task-18 client/assignment admin, and everything downstream that needs per-user identity) should import get_current_user / require_role from app.auth, and use apiFetch from api.ts for all frontend requests instead of calling fetch directly.

Testing coverage:

- Backend: pytest, 15 of 15 passed (8 pre-existing, 7 new: 6 in test_auth.py plus 1 new /users test in test_app.py).

- Frontend: vitest, 6 of 6 passed (2 pre-existing App tests updated for fetch mocking, 2 new api.test.ts, 2 new UserSwitcher.test.tsx).

- Lint: ruff and eslint both clean (0 errors, 0 warnings).

- Manually started the backend and confirmed GET /users returns real seeded data end-to-end.

- E2E: skipped -- see notes above (backend not auto-started in Playwright config).

Future considerations:

- task-18 (client/assignment admin) can now use require_role("admin") directly to satisfy its AC #4.

- Real authentication, if ever added, should be a drop-in replacement for get_current_user's header-reading logic -- the User table and role model don't need to change.

CODE REVIEW: Approved with 1 minor -- api.ts hardcodes http://localhost:8000 rather than an env var; fine for now since no deployment concept exists yet, revisit when it does.
<!-- SECTION:NOTES:END -->
