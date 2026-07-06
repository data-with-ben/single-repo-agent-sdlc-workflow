---
id: TASK-38
title: Fix WeeklyCalendar crash for unauthenticated/no-user-selected visitors
status: Done
assignee:
  - '@agent'
created_date: '2026-07-06 02:49'
updated_date: '2026-07-06 02:58'
labels: []
dependencies: []
references:
  - fix/task-38-weekly-calendar-401-crash
priority: high
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On a fresh browser with no user selected yet, every /me/* request returns 401. WeeklyCalendar.tsx does not check response.ok before parsing JSON and setting state, unlike every other data-fetching component in the app (Portfolio, Scoreboard, MorningProjection, Brackets, and ClientAdmin all guard this correctly). The 401 body ({detail: ...}) gets set as the entries/clients state, then a for-of loop over entries throws entries is not iterable during render, crashing the whole app to a white screen with no error boundary anywhere in the tree. Discovered by manually loading a freshly-seeded preview environment in a clean browser.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 WeeklyCalendar.tsx guards both its /me/time-entries and /me/clients fetches with a response.ok check, matching the pattern already used elsewhere in the codebase
- [x] #2 Loading the app with no user selected (fresh localStorage) no longer crashes to a white screen
- [x] #3 Existing WeeklyCalendar test suite continues to pass, plus a new test covers the unauthenticated/401 case
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Root cause: WeeklyCalendar.tsx around line 160 called response.json() on both /me/time-entries and /me/clients fetches without checking response.ok first, unlike every other data-fetching component (Portfolio, Scoreboard, MorningProjection, Brackets, ClientAdmin). On a fresh browser with no user selected, both requests 401, the error body got set as component state, and a subsequent for-of loop over the non-array entries state threw entries is not iterable during render, crashing the whole app to a white screen with no error boundary anywhere in the tree.

Fix: added response.ok checks to both fetches, matching the established pattern elsewhere. Also fixed WeeklyCalendar.test.tsx mock fetch helper, which never set ok at all, silently masking the bug in every existing test -- now sets ok true for the happy path and adds a dedicated unauthenticated-response test case.

Verified: full frontend suite passes (42 tests, 1 new), lint and build clean, and manually confirmed live in a running preview environment that a fresh unauthenticated load no longer crashes.
<!-- SECTION:NOTES:END -->
