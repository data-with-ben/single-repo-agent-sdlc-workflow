---
id: TASK-37
title: Verify WeeklyCalendar perfect-day check after timestamp UTC-marker fix
status: Done
assignee:
  - '@agent'
created_date: '2026-07-05 02:22'
updated_date: '2026-07-05 03:27'
labels:
  - backend frontend bug
dependencies: []
references:
  - feature/task-37-weekly-calendar-perfect-day-fix
modified_files:
  - backend/app/main.py
  - backend/tests/test_main_timeentry.py
  - frontend/vite.config.ts
  - frontend/src/WeeklyCalendar.tsx
  - frontend/src/WeeklyCalendar.test.tsx
  - >-
    backlog/backlog/tasks/task-37 -
    Verify-WeeklyCalendar-perfect-day-check-after-timestamp-UTC-marker-fix.md
priority: high
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
task-21 found and fixed a real bug in backend _serialize_entry: projected_at/logged_at/updated_at/first_submitted_at were serialized via Python isoformat() with no Z suffix or UTC offset, even though they always represent true UTC instants. Verified empirically that a spec-compliant JS engine parses a Z-less timestamp as local time, not UTC -- a full timezone-offset misread (e.g. 4 hours in EDT) that can even flip which calendar day an event is attributed to near midnight. The fix (append Z at serialization) landed on task-21s branch (feature/task-21-morning-project-day, not yet merged to main). WeeklyCalendar.tsx (task-20, feature/task-20-weekly-calendar-day-entry, also not yet merged) has an identical projected_at-based perfect-day check (computeLivePointsHint in WeeklyCalendar.tsx) that reads the same unmarked timestamp format and is very likely affected by the same bug. This was not verified directly since task-20 is already Done/pushed and was not reopened for this fix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Confirm whether WeeklyCalendars perfect-day check (computeLivePointsHint) produces the correct result once both task-20 and task-21s branches are merged together (the fix landing via task-21 should resolve it for free, since both read the same backend-serialized field)
- [x] #2 If any other frontend code introduced after task-21 parses projected_at/logged_at/updated_at/first_submitted_at via new Date(), confirm it is not relying on the old (unmarked, mis-parsed-as-local) behavior
- [x] #3 Add a regression test in WeeklyCalendar.test.tsx (or wherever the merged code lands) that pins a UTC-marked timestamp via a fixed system clock and asserts the perfect-day bonus is computed using the correct local hour, not a timezone-shifted one
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-37:

Both task-20 (WeeklyCalendar.tsx) and task-21 (backend timestamp Z-suffix fix) branches
are still unmerged into main, and this workflow has no auto-merge step, so this branch
will be built from main by porting over the combination of both changes, following the
same duplicate-across-branches pattern already used for CORS and /me/time-entries.

1. Port the task-21 backend fix onto this branch: copy the four Z-suffixed isoformat
   lines in backend/app/main.py _serialize_entry (projected_at, logged_at, updated_at,
   first_submitted_at) verbatim from feature/task-21-morning-project-day, plus its
   existing regression test test_serialized_timestamps_are_marked_as_utc in
   backend/tests/test_main_timeentry.py (or wherever it lives), plus the CORS
   middleware and /me/time-entries endpoint that task-20/21 both depend on (already
   duplicated pattern from prior tasks), so the backend on this branch is self
   consistent and testable standalone.

2. Port task-20's frontend WeeklyCalendar.tsx and its test file onto this branch,
   along with the App.tsx wiring needed to render it, matching task-20's shipped
   version verbatim (no logic changes) since AC #1 only requires confirming behavior
   once combined with the fix, not modifying WeeklyCalendar's logic itself.

3. AC #1 (perfect-day check produces correct result once combined): verified by
   inspection plus a new regression test (see step 4) â€” computeLivePointsHint parses
   existingProjectedAt via new Date(...), which is correct once the value carries the
   Z suffix; no code change is required in WeeklyCalendar.tsx itself, only the
   presence of the already-ported backend fix.

4. AC #3 (regression test): add a test to WeeklyCalendar.test.tsx that pins
   vi.setSystemTime() to a fixed instant, supplies a UTC-marked (Z-suffixed)
   projected_at timestamp whose UTC hour is before 11am but whose naive-local
   interpretation would NOT be before 11am (or vice versa) in the test's simulated
   timezone, and asserts the perfect-day bonus in computeLivePointsHint's return value
   is computed from the correct (UTC-interpreted) hour. This directly proves the
   combination behaves correctly rather than relying on inspection alone.

5. AC #2 (other frontend code parsing these timestamp fields): grep both branches'
   frontend/src for new Date( usages against projected_at/logged_at/updated_at/
   first_submitted_at. Confirmed only two call sites exist across both branches:
   WeeklyCalendar.tsx's computeLivePointsHint (covered by step 3/4) and
   MorningProjection.tsx's clientStatus (frontend/src/MorningProjection.tsx). Port
   MorningProjection.tsx and its test file onto this branch too, and confirm (by
   reading, no logic change needed) that clientStatus does a direct new Date(...)
   comparison with no compensating offset hack for the old broken behavior â€” so it
   is also fixed for free. Document this confirmation in the task notes as the
   AC #2 evidence, no code change required there since it does not need a new
   regression test of its own (AC #3 only asks for one in WeeklyCalendar.test.tsx).

6. Run the full backend and frontend test suites on this branch to confirm nothing
   regresses now that both dependencies' code lives together.

7. This branch intentionally does not touch either task-20 or task-21's original
   branches â€” once both are eventually merged into main, this verification and its
   new regression test should be re-homed there (or simply prove itself redundant
   once the real merge happens, since the same code will already exist). Document
   this in implementation notes as the expected resolution path, matching the
   pattern already used for other duplicated-across-branches work this session.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (2 warnings, 1 minor): (1) regression test must force a non-UTC timezone explicitly rather than relying on ambient TZ, since a UTC-default runner would make old-vs-fixed behavior indistinguishable; (2) drop porting CORS middleware and /me/time-entries endpoint -- AC1-3 are provable via frontend unit tests with mocked fetch, no live backend needed; (3) MorningProjection.tsx can be reviewed via git show for AC2 confirmation without full App.tsx wiring.

E2E TESTS: Skipped -- this task verifies existing timestamp-parsing logic at the unit level (WeeklyCalendar.test.tsx, backend test_main_timeentry.py); no new user-facing workflow was introduced, and WeeklyCalendar/MorningProjection were not wired into App.tsx on this branch since doing so is unnecessary for AC1-3 (all provable via mocked-fetch unit tests, per hostile plan review scope trim).

IMPLEMENTATION NOTES: Ported task-21's Z-suffix timestamp fix (backend/app/main.py _serialize_entry) and task-20's WeeklyCalendar.tsx + test onto this branch (built from main, since neither dependency branch is merged and this workflow has no auto-merge step -- same duplicate-across-branches pattern used for CORS/objective_engine/pytest-cov). Trimmed scope per hostile plan review: did not port the CORS middleware or /me/time-entries endpoint, since AC1-3 are provable via unit tests with mocked fetch, no live backend call needed. Added a new WeeklyCalendar.test.tsx case that pins a Z-suffixed projected_at (14:30 UTC) and verifies the perfect-day bonus is computed from the correct local hour (10:30 EDT, before the 11am cutoff) -- manually verified this test fails (15 pts, no perfect-day) if the Z suffix is stripped, and passes (20 pts, perfect day) with it present, proving real sensitivity to the fix. Pinned vite.config.ts test env to TZ=America/New_York so this distinction holds regardless of the CI runner's ambient timezone (a UTC-default runner would make old-vs-fixed behavior indistinguishable). Reviewed MorningProjection.tsx's clientStatus (the only other frontend call site parsing these timestamp fields via new Date) and confirmed it does a direct comparison with no compensating offset hack -- also fixed for free, no code change needed there (AC2). Backend: 39 tests pass (added test_serialized_timestamps_are_marked_as_utc, ported from task-21). Frontend: 18 tests pass (8 in WeeklyCalendar.test.tsx, including the new regression test). E2E skipped -- no new user-facing workflow. This branch does not touch task-20 or task-21's original branches; once both are eventually merged into main, this verification becomes redundant with (or should be reconciled into) the merged code.

CODE REVIEW: Approved with 0 issues. Verified ruff and eslint pass clean on all changed files. Confirmed by direct experiment that the new regression test is sensitive to the fix (fails at 15pts without the Z suffix, passes at 20pts/perfect-day with it).

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-skip, notes, code-review, this audit).
<!-- SECTION:NOTES:END -->
