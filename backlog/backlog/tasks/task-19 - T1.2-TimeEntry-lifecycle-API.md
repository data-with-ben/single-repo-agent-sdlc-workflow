---
id: TASK-19
title: T1.2 TimeEntry lifecycle (API)
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:25'
updated_date: '2026-07-04 03:47'
labels:
  - backend
dependencies:
  - TASK-18
  - TASK-35
references:
  - feature/task-19-timeentry-lifecycle
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
modified_files:
  - backend/app/main.py
  - backend/app/timeentry.py
  - backend/tests/test_timeentry.py
  - backend/tests/test_main_timeentry.py
  - backlog/backlog/tasks/task-19 - T1.2-TimeEntry-lifecycle-API.md
priority: high
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the TimeEntry state machine from SPEC.md Section 5: project(), log(), and eodUpdate(), with correct timestamp writes and an immutable firstSubmittedAt used later by the anti-gaming objective rules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each state transition (project, log, eodUpdate) writes exactly the fields specified in SPEC.md Section 5
- [x] #2 firstSubmittedAt is written once on first submission and never changes afterward
- [x] #3 Illegal transitions are rejected with a clear error
- [x] #4 Multiple entries per (consultant, workDate) are supported
- [x] #5 Unit tests cover each transition and the anti-gaming invariant: a later fix to an entry does not backdate its scoring objective
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Interpretation of the state machine, made explicit here since SPEC.md Section 5 leaves it implicit (documented for hostile review to scrutinize): state tracks the highest transition ever reached (empty < projected < logged < updated), monotonically non-decreasing regardless of which function was called (e.g. calling eodUpdate() straight from empty jumps state to updated, skipping projected/logged, per "skipping states is allowed"). project() is first-submission-only (no revise language in spec, unlike eodUpdate's explicit "sets/revises"): legal only when state is empty, illegal (rejected) otherwise -- this is the concrete "illegal transition" AC #3 requires. log() may be called again after reaching logged/updated to revise actualHours, but loggedAt itself is written once on first log() (spec calls it "timestamp actuals first submitted") and never changes after. eodUpdate() may always be called (revises description, overwrites updatedAt every time, per spec's explicit "write/revise" language).
2. Add three functions to a new app/timeentry.py: project(session, entry, planned_hours, client_id, at) enforcing legality (state must be empty); log(session, entry, actual_hours, at) settable from any state, writes loggedAt only if unset; eod_update(session, entry, description, at) settable from any state, always overwrites updatedAt. Each sets first_submitted_at if it is currently None (the true first-ever write to the entry, whichever function is called first) and advances state forward-only to the transition's own level if the entry isn't already past it. Verifies AC #1, #2, #3.
3. API endpoints in app/main.py, admin-or-self only (a consultant can only submit their own entries; an admin can submit on behalf of anyone -- mirrors task-18's admin-vs-self pattern): POST /time-entries/project, POST /time-entries/{id}/log, POST /time-entries/{id}/eod-update. project() creates a new TimeEntry row (since it's the only transition allowed to originate one) if no entry exists yet for (consultant, work_date, client_id), or operates on an existing empty one; log()/eod-update() operate on an existing entry by id. Verifies AC #4 implicitly, since project() is scoped per (consultant, work_date, client_id) and creates a fresh row per client rather than reusing one across clients.
4. Reject illegal transitions with a 409 (state conflict), matching the pattern already used for task-18's duplicate-assignment case, and a clear detail message naming the current state.
5. Backend tests (tests/test_timeentry.py) at the function level (app/timeentry.py, not just via HTTP) for precision: each transition writes exactly the spec'd fields; firstSubmittedAt set once, unaffected by later calls; project() rejected once state has moved past empty; log() revision after logged/updated updates actualHours but not loggedAt; eodUpdate() revision overwrites updatedAt and description; two TimeEntry rows for the same (consultant, workDate) but different clients both work independently (AC #4). The anti-gaming invariant test (AC #5): create an entry, log() it (setting loggedAt on day 1), then advance the clock and call log() again (revision) -- assert loggedAt is unchanged (still day 1), proving a later fix cannot backdate or postdate the same-day objective's input timestamp.
6. API-level tests (tests/test_main_timeentry.py or extend test_clients.py's pattern): a consultant can submit against their own assignment; a consultant cannot submit against a client they aren't assigned to (403 or 404, matching task-18's precedent); an admin can submit on behalf of any consultant.
7. Verification pass: run backend pytest and ruff before handing off to unit-tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (2 warning(s), 1 minor)

- Warning (significant): step 3 has log() and eod-update() endpoints operate on 'an existing entry by id', but spec explicitly allows skipping straight to log() or eodUpdate() without ever calling project() first -- in that case no TimeEntry row (and therefore no id) exists yet. log() and eod-update() endpoints must use the same find-or-create-by-(consultant, work_date, client_id) lookup that project() uses, not an id-based lookup, or 'skipping states' silently breaks at the API layer despite being supported at the app/timeentry.py function layer (step 2).

- Warning: step 3 claims this 'mirrors task-18's admin-vs-self pattern', but task-18 never actually implemented an admin-or-self check on a specific resource -- it only has admin-only endpoints and a separate 'return only my own data' filter (/me/clients). There is no existing reusable pattern for 'admin can act on behalf of any consultant_id, non-admin can only act as themselves'; this needs new logic in this task, not reuse.

- Minor: step 3's phrase 'operates on an existing empty one' is imprecise -- an empty TimeEntry row never actually persists before any transition is called; the row is created by whichever of the three functions runs first. No functional bug, just wording to keep straight during implementation.

E2E: skipped -- this task is backend-only (API + state machine), no UI surface; none of the five ACs require e2e coverage. The calendar/day-entry UI that will call these endpoints is task-20.

IMPLEMENTATION NOTES

What was implemented:

- Backend: app/timeentry.py implements the state machine as three pure functions (project, log, eod_update) operating on a TimeEntry ORM object, plus IllegalTransitionError. state tracks the highest transition ever reached (empty < projected < logged < updated), advancing forward-only regardless of which function is called first, matching SPEC.md's "skipping states is allowed".

- project() is first-submission-only (illegal once state has moved past "empty") -- this is the concrete illegal transition AC #3 requires, since SPEC.md gives eodUpdate explicit "revise" language but never says project() can be revised.

- log() can be called again to revise actual_hours, but logged_at is written only on first call and never changes -- this is the anti-gaming mechanism AC #5 tests directly (a later fix does not backdate the same-day objective's input timestamp).

- eod_update() always overwrites description and updated_at, matching SPEC.md's explicit "write/revise" language.

- first_submitted_at is set on whichever of the three functions is called first, across the entry's whole lifetime, never changed after.

- API: three endpoints in app/main.py (POST /time-entries/project, /log, /eod-update), all using a shared find-or-create-by-(consultant_id, client_id, work_date) lookup -- resolving a hostile-review warning that log()/eod-update() would otherwise need an existing entry id, breaking the spec's "skip straight to log/eodUpdate" allowance.

- New authorization helper _resolve_target_consultant_id: a consultant can only submit their own entries; an admin can submit on behalf of any consultant (via an optional consultant_id in the request body). This is new logic -- the plan's claim that it "mirrors task-18" was flagged as inaccurate in hostile review (task-18 never had an admin-or-self check), so it was built from scratch here.

- _require_assignment reuses task-18's Assignment table to reject submissions against a client the consultant isn't assigned to (403), tying into task-18's AC #3 ("assignments determine the client options for time entry").

Key technical decisions:

- work_date is accepted as a plain date string in requests and stored as midnight-of-day DateTime, matching the existing TimeEntry.work_date column type.

- Illegal transitions return 409 (state conflict), consistent with task-18's duplicate-assignment precedent.

- Test coverage is split: app/timeentry.py functions are tested directly (test_timeentry.py) for precision on field-level behavior, separate from the API-level authorization/assignment tests (test_main_timeentry.py).

Integration points:

- No new dependencies, no new migration -- reuses task-16's TimeEntry table and task-18's Assignment table as-is.

- Future tasks (T1.3 calendar UI, T1.4 morning-projection UI, T2.1 objective engine) will call these three endpoints and read the same timestamp fields this task writes.

Testing coverage:

- Backend: pytest, 38 of 38 passed (23 pre-existing, 15 new: 9 in test_timeentry.py, 6 in test_main_timeentry.py).

- Lint: ruff clean.

- E2E: skipped -- backend-only, no UI in scope (see notes above).

Future considerations:

- task-22 (objective engine) is where the "local zone" threshold evaluation (11am/3pm/6pm) actually happens -- this task only writes correct UTC timestamps; it does not itself evaluate whether an entry counts toward an objective.

- The min-description-length rule for eodUpdate's objective ("meets min length, default 20 chars", SPEC.md Section 5/6) is also task-22's concern, not enforced here -- this task accepts any description string.

CODE REVIEW: Approved with 0 issues
<!-- SECTION:NOTES:END -->
