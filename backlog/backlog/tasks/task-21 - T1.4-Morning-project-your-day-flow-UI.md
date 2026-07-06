---
id: TASK-21
title: T1.4 Morning project-your-day flow (UI)
status: Done
assignee:
  - '@agent'
created_date: '2026-07-03 15:26'
updated_date: '2026-07-05 02:21'
labels:
  - frontend
dependencies:
  - TASK-19
  - TASK-35
references:
  - feature/task-21-morning-project-day
modified_files:
  - backend/app/main.py
  - backend/tests/test_main_timeentry.py
  - frontend/src/App.tsx
  - frontend/src/MorningProjection.tsx
  - frontend/src/MorningProjection.test.tsx
  - e2e/playwright.config.ts
  - e2e/tests/morning-projection.spec.ts
  - backlog/backlog/tasks/task-21 - T1.4-Morning-project-your-day-flow-UI.md
priority: high
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A dedicated pre-11am screen where a consultant projects their day: choose clients and set planned hours ahead of the 11am scoring cutoff. UI should match wireframe 1 once that reference image is attached to this task's assets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The screen calls the project() transition from the T1.2 lifecycle API
- [x] #2 The screen shows time remaining until the 11am cutoff
- [x] #3 The screen clearly indicates once the 11am objective is locked in or has been missed
- [x] #4 The UI matches the layout described for wireframe 1 (client/hour picker with a countdown to 11am)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Backend: add GET /me/time-entries?start=YYYY-MM-DD&end=YYYY-MM-DD to app/main.py, identical in shape to the read endpoint task-20 already built on its own not-yet-merged branch (same filter by consultant_id and work_date range via _serialize_entry) -- needed since this screen must show already-locked-in/missed state on page load, not only after a fresh submission. Backend test added alongside existing time-entry tests. Noting explicitly: if task-20 merges first, this will be a duplicate addition and should collapse to one copy during that merge -- not a blocker now, just a known future merge-conflict point across two independently-developed branches.
2. Frontend: add src/MorningProjection.tsx -- fetches GET /me/clients (assigned clients) and GET /me/time-entries?start=today&end=today on mount. For each assigned client, renders one row: an hours input + submit button while the client has not yet been projected today, or a locked-in/missed status line once it has a recorded outcome for today (AC #1, #4).
3. Per-client status for today (AC #3), derived from that clients today entry (if any) and the current local time: locked in if projected_at is set and its local time is at or before 11:00 on the work date; missed-late if projected_at is set but after 11:00; missed-not-projected if no projected_at and the current local time is already past 11:00; otherwise open (before 11:00, not yet projected) -- shows the input+submit row. Per SPEC.md Section 5s anti-gaming note (skipping/late states are allowed but forfeit the objective), a late or post-cutoff submission is still permitted through the same input -- only the status label changes, submission is never blocked.
4. Countdown (AC #2): computed client-side from the browsers local Date against today at 11:00:00 -- while now is before 11:00, render remaining time (updates on an interval, e.g. every 30s, since second-level precision is not required by the AC); once now is at or after 11:00, render a fixed cutoff-passed message instead of a live countdown.
5. Submission calls POST /time-entries/project with client_id, work_date=today, planned_hours from that rows input (task-19s existing endpoint) -- this screen only ever calls project(), never log()/eod-update (those belong to task-20s separate actuals/EOD screen). A 409 (IllegalTransitionError, already past empty) is treated the same as a successful reload -- refetch todays entries so the row settles into its correct locked-in/missed status rather than surfacing the error, since a 409 here just means another tab/session already projected this client today.
6. Wire MorningProjection into App.tsx above ClientAdmin, as the start-of-day screen a consultant sees first.
7. Frontend tests (MorningProjection.test.tsx), using vi.useFakeTimers/vi.setSystemTime to pin now deterministically (the approach already proven in WeeklyCalendar.test.tsx, avoiding flakiness from the real system clocks weekday/hour): renders open state and submits project() before 11am; renders locked-in state when an existing entry has projected_at before 11am today; renders missed state when now is past 11am and no entry exists; renders the countdown before 11am and the cutoff-passed message after.
8. E2E: add a backend webServer entry to e2e/playwright.config.ts (this branch does not yet have the one task-20 independently built on its own branch -- same cross-platform pattern: migrate + seed + uvicorn against a dedicated DATABASE_URL, python path branched on process.platform). Add e2e/tests/morning-projection.spec.ts covering the open-state render and a real project() submission against seeded data.
9. Verification pass: run backend pytest and ruff, frontend npm test and npm run lint, npx playwright test for e2e, and manually start both servers to submit a real projection against seeded data before handing off to unit-tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (2 warning(s), 1 minor)

- Warning: GET /me/clients does not filter by client status, so an archived client would still show a projection row on this screen. The plan does not address whether archived clients should be excluded. Not blocking -- this is an inherited gap already present unaddressed in task-20s WeeklyCalendar, not something task-21 introduces fresh -- but resolve during implementation by deciding whether to filter status active in this screen specifically.
- Warning: step 7s fake-timer tests must construct any mocked entrys projected_at relative to the same pinned now (via vi.setSystemTime), not a real wall-clock date -- this exact class of bug (date construction inconsistent with the pinned clock) already caused a real failure once in task-20s test suite and should be checked explicitly rather than re-discovered.
- Minor: the 30s countdown update interval is a reasonable, unspecified implementer choice -- the AC does not require higher precision.

Plan deviation: manual verification with real seeded data revealed a serious pre-existing bug affecting AC #3s correctness, not introduced by task-21 but first surfaced here. Backend _serialize_entry (from task-19) serializes naive-UTC datetimes (projected_at, logged_at, updated_at, first_submitted_at) via Python isoformat() with no Z suffix or offset. Verified empirically with node: new Date(2026-07-05T02:10:26.138292) (no Z) is parsed by V8 as LOCAL time, not UTC -- in this EDT (UTC-4) environment, a true submission at 22:10 local was misread by the frontend as 02:10 local the next day, a 4-hour shift that can also flip which calendar day an event is attributed to near midnight. This directly breaks the locked-in vs missed-late determination in MorningProjection.tsx (and the identical projected_at-based perfect-day check already shipped in task-20s WeeklyCalendar.tsx). Fixed by appending Z to all four isoformat() calls in _serialize_entry, since these naive datetimes always represent true UTC instants (datetime.now(timezone.utc).replace(tzinfo=None)) throughout the codebase. Added a regression test (test_serialized_timestamps_are_marked_as_utc) and verified the fix directly: the same real submission now round-trips through JS Date parsing to the correct local hour. Also duplicated task-1s not-yet-merged CORS middleware onto this branch (same pattern already accepted for the /me/time-entries endpoint) since e2e tests cannot exercise any real API call in a browser without it -- expected to collapse into one copy whenever these branches are merged.

IMPLEMENTATION SUMMARY

What was implemented:
- backend/app/main.py: added GET /me/time-entries?start&end (identical shape to task-20s not-yet-merged version, needed here to show already-locked-in/missed state on page load). Also duplicated task-1s not-yet-merged CORS middleware (same accepted pattern) since e2e tests cannot exercise any real API call in a browser without it. Fixed a real, previously-undetected timestamp serialization bug in _serialize_entry (see Key technical decisions).
- backend/tests/test_main_timeentry.py: 3 tests for the /me/time-entries endpoint (range filtering, caller-only scoping, 401 without auth) plus a regression test locking in the Z-suffix timestamp fix.
- frontend/src/MorningProjection.tsx (new): fetches assigned clients and todays entries; renders one row per client -- an hours input + submit (calling POST /time-entries/project) while that client has not yet been locked in, or a status label (Locked in / Missed (projected late) / Missed (not projected)) once it has. A live countdown to the 11am cutoff is shown above the list, switching to a fixed Cutoff passed message once past 11am.
- frontend/src/MorningProjection.test.tsx (new): 4 tests using vi.useFakeTimers/vi.setSystemTime to pin now deterministically -- open state + submission before cutoff, locked-in state, missed-not-projected state (still allows submission), missed-late state.
- frontend/src/App.tsx: wired MorningProjection in above ClientAdmin.
- e2e/playwright.config.ts: added the same backend-starting webServer entry independently derived in task-20 and task-1 (this branch predates both, so neither was present here yet).
- e2e/tests/morning-projection.spec.ts (new): open-state render and a real project() submission against seeded data.

Key technical decisions:
- Per-client status derivation (open / locked-in / missed-late / missed-not-projected) is based purely on that clients today entrys projected_at field, not its state field -- deliberately, since an entry can reach logged/updated state with projected_at still unset (if a consultant used the actuals screen without ever projecting), and the status shown here must reflect the 11am objective specifically, not the entrys overall lifecycle state.
- Per SPEC.md Section 5s anti-gaming note (skipping/late states are allowed but forfeit the objective), the input+submit row stays available for missed-not-projected (past cutoff, not yet projected) -- only locked-in and missed-late (already has a projected_at) hide it. A 409 from an already-projected entry is treated as a normal reload trigger, not an error to surface.
- Countdown/cutoff comparisons use the browsers own local Date, matching the existing precedent from task-20s WeeklyCalendar (a documented simplification pending a stored per-user timezone).
- SIGNIFICANT FIX: manual verification with real seeded data surfaced that _serialize_entry (backend/app/main.py, from task-19) serializes naive-UTC datetimes via Python isoformat() with no Z suffix. Verified empirically with node that a spec-compliant JS engine parses a Z-less ISO datetime string as LOCAL time, not UTC. In this EDT (UTC-4) test environment, a true submission at 22:10 local was misread as 02:10 local the next day -- a 4-hour shift that can flip which calendar day an event is attributed to near midnight. This directly breaks locked-in vs missed-late here, and the identical projected_at-based perfect-day check already shipped in task-20s WeeklyCalendar.tsx. Fixed by appending Z to all four timestamp fields in _serialize_entry (projected_at, logged_at, updated_at, first_submitted_at). Verified the fix directly: the same real submission now round-trips through JS Date parsing to the correct local hour. A regression test (test_serialized_timestamps_are_marked_as_utc) locks this in. This bug predates task-21 (introduced in task-19) and independently affects task-20s already-shipped code -- flagging for a follow-up backlog task since task-20 is already Done/pushed and should not be silently reopened here.

Integration points:
- No new dependencies.
- Two known duplicate-until-merge additions on this branch: the /me/time-entries endpoint (also on task-20s branch) and the CORS middleware (also on task-1s branch) -- expected to collapse into one copy each whenever those branches merge with this one, same as already noted on task-20 and task-1.

Testing coverage:
- Backend: 42 pytest passed (38 existing + 1 endpoint range test + 1 caller-scoping test + 1 auth test + 1 Z-suffix regression test), ruff clean.
- Frontend: 14 vitest passed (10 existing + 4 new MorningProjection tests), eslint clean.
- E2E: 2 new tests, both passing, results committed under e2e/test-results/.
- Manual verification: started both servers against seeded data, submitted a real projection for consultant 3 / Acme Corp, confirmed persistence and confirmed the Z-suffix fix produces the correct local hour via a direct node check.

Future considerations:
- Recommend filing a follow-up backlog task documenting that task-20s WeeklyCalendar.tsx perfect-day check has the same latent timestamp-parsing bug this task just fixed at the source (_serialize_entry) -- once task-20s branch is merged after this ones fix, or once both are merged together, that check will already be correct without further changes, but this should be verified rather than assumed.
- Once task-22s canonical objective engine exists, the client-side locked-in/missed derivation here should be revisited to match its authoritative scoring rather than being independently reimplemented.
- The archived-client-still-shown gap flagged during hostile plan review (GET /me/clients does not filter by status) was not fixed here, consistent with task-20 leaving the same gap unaddressed -- worth a dedicated pass across both screens if prioritized.

CODE REVIEW: Approved with 2 minor suggestions.

No critical or major issues found. Diff is clean and matches existing conventions (MorningProjection.tsx mirrors WeeklyCalendar.tsx/ClientAdmin.tsx patterns for fetch, error handling via response.ok checks, and countdown/time derivation). Verified the Z-suffix timestamp fix is correct and safe: every write path (timeentry.py via main.py) constructs these fields as datetime.now(timezone.utc).replace(tzinfo=None), so the invariant that naive datetime = true UTC instant holds app-wide, not just for this tasks new code. No other frontend code on this branch parses these fields via new Date(...), so nothing relied on the old buggy behavior.

Minor, non-blocking:
- seed.py constructs demo projected_at/logged_at/updated_at values as readable local-feeling hours (9:30am, 4pm, etc). With the Z-suffix fix, these now correctly display shifted by the viewers UTC offset (e.g. a seeded 9:30am naive value renders as 9:30am UTC = 5:30am EDT), which may look surprising in a demo/UI walkthrough even though it is now technically correct given the codebases actual invariant. Not a logic bug -- worth a look if demo readability matters, but out of this tasks scope.
- handleSubmit in MorningProjection.tsx does not check the POST responses status before reloading entries, matching the same pre-existing pattern already accepted in ClientAdmin.tsx and WeeklyCalendar.tsx (no error surfacing anywhere in this frontend yet) -- consistent with project convention, not a new gap.

Requirements alignment: all 4 ACs verified against real running code and a real seeded-data submission (see AC verification and Implementation Notes). Scope is appropriately minimal; the two duplicate-until-merge additions (CORS middleware, /me/time-entries endpoint) and the timestamp serialization fix are all clearly justified and documented as plan deviations, not silent expansion. No security issues (ORM/Pydantic throughout, CORS origin allowlist is not a wildcard). No unnecessary dependencies.

SELF-IMPROVEMENT: hostile-plan-review has not, across two separate plans (task-20 and task-21) that both parse backend-supplied datetime fields client-side for time-of-day comparisons, flagged the risk of unmarked (no Z/offset) timestamp serialization causing JS Date to misparse UTC as local time. This is a systemic hazard specific to this stacks pattern (Python naive datetime.now(timezone.utc).replace(tzinfo=None) values, serialized via .isoformat() with no explicit UTC marker, then parsed in the frontend via new Date(iso_string) for hour/day comparisons) -- not a one-off mistake, since it was only caught both times via manual verification with real seeded data, not planning or code review. Recommend adding a standing hostile-plan-review dimension (or a note in plan-task/code-review) for this codebase specifically: whenever a plan involves parsing a backend-supplied timestamp client-side for time-of-day or same-day comparisons, verify the serialized format carries an explicit UTC marker (Z suffix or offset) before trusting the comparison, rather than relying on manual verification to catch it after the fact.
<!-- SECTION:NOTES:END -->
