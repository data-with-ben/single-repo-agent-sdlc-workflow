---
id: TASK-18
title: T1.1 Client and assignment admin (API + UI)
status: Done
assignee:
  - '@agent'
created_date: '2026-07-03 15:25'
updated_date: '2026-07-04 03:13'
labels:
  - backend frontend
dependencies:
  - TASK-17
  - TASK-35
references:
  - feature/task-18-client-assignment-admin
modified_files:
  - backend/app/main.py
  - backend/tests/test_clients.py
  - frontend/src/App.tsx
  - frontend/src/ClientAdmin.tsx
  - frontend/src/ClientAdmin.test.tsx
  - backlog/backlog/tasks/task-18 - T1.1-Client-and-assignment-admin-API-UI.md
priority: high
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CRUD for clients, and the ability to assign or unassign consultants to clients. This determines which clients a consultant can log time against downstream. UI should match wireframe 3 once that reference image is attached to this task's assets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An admin can create and archive a client
- [x] #2 An admin can assign and remove a consultant from a client
- [x] #3 A consultant's assignments determine the client options returned for time entry
- [x] #4 Non-admins cannot mutate clients or assignments
- [x] #5 The UI matches the layout described for wireframe 3 (client list with assignment controls)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Backend endpoints in app/main.py, all using get_current_user/require_role("admin") from app.auth (task-35): GET /clients (any valid user, lists all clients id/name/status) -- viewing is not mutation, so no admin requirement, only a valid identity. POST /clients (admin only, body {name}, creates an active client). POST /clients/{client_id}/archive (admin only, sets status=archived). Verifies AC #1.
2. GET /clients/{client_id}/assignments (admin only, lists assigned consultants: id/display_name/start_date) and POST /clients/{client_id}/assignments (admin only, body {consultant_id}, creates an Assignment row) and DELETE /clients/{client_id}/assignments/{consultant_id} (admin only, hard-deletes the Assignment row -- Assignment has no status field, and no AC requires preserving removed-assignment history). Verifies AC #2.
3. GET /me/clients (any valid user, returns the clients the calling user is currently assigned to via their Assignment rows) -- this is the concrete, testable form of AC #3 ("determine the client options returned for time entry"), since the actual time-entry screen doesn't exist yet (later task).
4. AC #4 (non-admins cannot mutate) is enforced entirely by require_role("admin") on the three mutating endpoints (create/archive client, assign/remove consultant) from step 1-2; GET endpoints stay open to any valid user since they're read-only.
5. Backend tests (tests/test_clients.py): cover create/archive as admin (200) and as non-admin (403); assign/remove as admin (200) and as non-admin (403); GET /clients and GET /clients/{id}/assignments return expected shapes; GET /me/clients reflects only the calling user's own assignments, not another user's.
6. Frontend: add src/ClientAdmin.tsx matching wireframe 3 (backlog/backlog/assets/wireframes/admin-view-1.png) -- a two-column layout: left column lists clients (name, consultant count, active/archived status, dimmed styling for archived, an "+ Add client" control); right column shows the selected client's assigned consultants (name, assignment start date) with a remove control per row and an "Assign" control to add a new one. Verifies AC #5.
7. Frontend: ClientAdmin fetches /users once (already available from task-35) to determine whether the current selected user has the admin role, and only renders the add/archive/assign/remove controls when true -- a UX nicety on top of the backend's own enforcement (AC #4), not a substitute for it.
8. Wire ClientAdmin into App.tsx below the existing UserSwitcher.
9. Frontend tests (ClientAdmin.test.tsx): renders the client list from a mocked fetch; admin controls are visible when the current user (from context) has the admin role and hidden otherwise; clicking Assign/remove calls the expected endpoint. Verifies AC #4 (frontend UX half) and #5.
10. Verification pass: run backend pytest and ruff, frontend npm test and npm run lint, and manually start both servers to click through create/archive/assign/remove against seeded data before handing off to unit-tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TASK ASSESSMENT - REFINEMENT NEEDED:

- AC #4 requires distinguishing admin from non-admin callers, but there is no authentication/session/current-user mechanism anywhere in SPEC.md or the T0-T5 backlog. SPEC.md Section 2 defines roles as 'permission flags on one account' but never specifies how a request identifies which account is calling. Section 9's screen list has no login screen either.

- This is not unique to task-18: the same gap blocks or under-specifies T1.2 (consultant logging only against their own assignments), T3.4 (hiding scores from non-admins), and every T4.x wallet/portfolio/trade operation ('per user' actions with no way to know which user).

- Needed to proceed: a decision on identity/auth approach for this build -- e.g. a minimal dev-mode current-user mechanism (a user-picker or a fixed request header identifying the caller, appropriate for a local/demo-scale app per SPEC.md's non-goals excluding real payroll/production concerns) vs. a real login flow (would need its own task ahead of T1.1 in the dependency order).

TASK ASSESSMENT - REFINEMENT RESOLVED: task-35 (dev-mode current-user identity mechanism) is now Done, providing require_role('admin') and get_current_user for exactly the AC #4 gap identified above. Re-assessed and passed.

HOSTILE PLAN REVIEW - PASSED (2 warning(s), 1 minor)

- Warning: Assignment has no uniqueness constraint on (consultant_id, client_id), so DELETE behavior when duplicate rows exist for the same pair is undefined. Resolve during implementation: either enforce no-duplicate on create (check-then-insert) so delete-by-pair is always unambiguous, or explicitly delete all matching rows.

- Warning: behavior for a nonexistent client_id/consultant_id, and for assigning a consultant to an archived client, is unspecified. Return 404 for unknown IDs rather than letting them surface as an unhandled DB error; recommend blocking new assignments against an archived client.

- Minor: ClientAdmin fetching /users independently duplicates UserSwitcher's own fetch, since currentUserContext only stores the selected id, not the full user list/roles. Acceptable for this task's scope (no shared state layer exists yet); worth consolidating in a future task.

E2E: skipped -- same infra limitation as task-35: exercising the client admin UI end-to-end requires the backend running, and Playwright's webServer config only auto-starts the frontend. Behavior is covered by real-request-cycle backend tests (test_clients.py) and React Testing Library tests for the UI (ClientAdmin.test.tsx), plus a manual live smoke test against seeded data confirming create/403 behavior end-to-end.

IMPLEMENTATION NOTES

What was implemented:

- Backend: seven endpoints in app/main.py, all built on task-35's get_current_user/require_role -- GET /clients (any valid user), POST /clients and POST /clients/{id}/archive (admin only), GET/POST /clients/{id}/assignments and DELETE /clients/{id}/assignments/{consultant_id} (admin only), and GET /me/clients (any valid user, returns the calling user's own assigned clients).

- Backend guards resolving hostile-review warnings: POST assignments rejects a nonexistent client or consultant with 404, rejects assigning to an archived client with 400, and rejects a duplicate (client, consultant) pair with 409 -- this also makes DELETE's behavior unambiguous since duplicates can no longer be created.

- Backend tests: tests/test_clients.py, 8 tests covering admin/non-admin for create+archive and assign+remove, the archived-client and unknown-id and duplicate-assignment guards, and that /me/clients only reflects the calling user's own assignments (not another user's).

- Frontend: src/ClientAdmin.tsx, a two-column layout matching wireframe 3 (backlog/backlog/assets/wireframes/admin-view-1.png) -- client list on the left (with archived styling and an add-client control), selected client's assigned consultants on the right (with a remove control per row and an assign dropdown of unassigned consultants). Admin-only controls are hidden client-side for non-admins as a UX nicety; the backend's require_role is what actually enforces AC #4.

- Frontend tests: src/ClientAdmin.test.tsx, 4 tests covering the client list rendering for any user, admin controls hidden/shown based on role, and the assign control appearing on client selection.

- Wired ClientAdmin into App.tsx below the existing UserSwitcher.

Key technical decisions:

- Assignment uniqueness is enforced at write time (409 on duplicate) rather than adding a DB-level unique constraint via a new migration -- keeps this task's migration footprint at zero, and the application-level check is sufficient given all writes go through this one endpoint.

- DELETE removes all matching (client, consultant) rows as a defensive measure, though duplicates can no longer occur going forward.

- ClientAdmin determines admin status by fetching /users and checking the current user's roles -- duplicates UserSwitcher's own /users fetch (flagged in hostile review as acceptable tech debt; no shared state layer exists yet to avoid it).

- Fixed a real ESLint error during implementation: an early-return branch in a useEffect was calling setState synchronously (react-hooks/set-state-in-effect), which the render's own `selectedClient && isAdmin` guard already makes unnecessary -- removed the redundant reset rather than restructuring further.

Integration points:

- No new dependencies (frontend or backend).

- No new migration -- reuses task-16's Client/Assignment/User tables as-is.

Testing coverage:

- Backend: pytest, 23 of 23 passed (15 pre-existing, 8 new).

- Frontend: vitest, 10 of 10 passed (6 pre-existing, 4 new).

- Lint: ruff and eslint both clean.

- Manually started the backend against seeded data and confirmed GET /clients, POST /clients (200 as admin), and POST /clients (403 as non-admin) end-to-end.

- E2E: skipped -- see notes above (backend not auto-started in Playwright config).

Future considerations:

- task-19 (TimeEntry lifecycle) will read from the same Assignment table (via /me/clients-style logic) to restrict which client a consultant can log time against.

- If a shared user/role context is ever added, ClientAdmin's separate /users fetch should be removed in favor of it.

CODE REVIEW: Approved with 0 issues
<!-- SECTION:NOTES:END -->
