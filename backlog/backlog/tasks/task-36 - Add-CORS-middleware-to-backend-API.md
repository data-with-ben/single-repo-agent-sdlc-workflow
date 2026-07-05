---
id: TASK-36
title: Add CORS middleware to backend API
status: To Do
assignee: []
created_date: '2026-07-05 00:30'
labels:
  - backend infra
dependencies: []
references:
  - feature/task-20-weekly-calendar-day-entry
priority: high
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The FastAPI backend has no CORS middleware configured anywhere, confirmed directly during task-20: an OPTIONS preflight to /me/time-entries returns 405 with no Access-Control-Allow-Origin header. This blocks every cross-origin browser request that carries the X-User-Id header (required by every authenticated endpoint), which is every screen in the app (ClientAdmin, UserSwitcher, WeeklyCalendar) when frontend and backend run on different origins/ports in local dev -- and would equally block a real deployed frontend calling a separately-hosted API. It also blocks e2e/tests/weekly-calendar.spec.ts (task-20) from actually running end to end; that spec and its webServer config are otherwise ready.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A cross-origin OPTIONS preflight to an authenticated endpoint (e.g. /me/time-entries) returns 200 with Access-Control-Allow-Origin and Access-Control-Allow-Headers covering X-User-Id
- [ ] #2 A real browser running the frontend dev server can successfully call the backend on its own port without a CORS error in the console
- [ ] #3 e2e/tests/weekly-calendar.spec.ts passes when run via npm run test:e2e
<!-- AC:END -->
