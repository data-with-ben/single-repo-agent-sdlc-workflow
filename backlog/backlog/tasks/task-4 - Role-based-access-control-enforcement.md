---
id: TASK-4
title: Role-based access control enforcement
status: To Do
assignee: []
created_date: '2026-07-03 13:28'
updated_date: '2026-07-03 15:24'
labels:
  - backend auth
  - flagged-for-removal
dependencies:
  - TASK-3
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Introduces the authorization layer that every protected feature will rely on: a way for endpoints to declare a minimum required role (consultant, manager, super_admin) and reject requests that don't meet it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Requests without a valid session/token are rejected from protected endpoints with a 401 response
- [ ] #2 Endpoints can declare a minimum required role and reject insufficient roles with a 403 response
- [ ] #3 A consultant can access their own timesheet endpoints but is blocked from manager-only endpoints
- [ ] #4 A manager can access manager-only endpoints for clients and consultants but not super-admin-only endpoints
- [ ] #5 A super admin can access all endpoints
- [ ] #6 Backend unit tests cover allow and deny cases for each role tier
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
