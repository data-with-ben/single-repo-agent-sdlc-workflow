---
id: TASK-35
title: Dev-mode current-user identity mechanism
status: To Do
assignee: []
created_date: '2026-07-04 02:35'
updated_date: '2026-07-04 02:37'
labels:
  - backend
  - frontend
  - foundation
dependencies:
  - TASK-16
priority: high
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
There is no login/session flow specified anywhere in SPEC.md or the T0-T5 backlog, yet almost every later task needs to know which user is calling: role checks (admin vs consultant) and per-user actions (a consultant's own timesheet, a user's own wallet/portfolio, trades). Rather than build real authentication (out of scope for a local/demo-scale game per SPEC.md's non-goals), add a minimal dev-mode mechanism: the caller is identified by a request header checked against the existing User table (from task-16's data model), with a simple frontend switcher to set it. This is a stand-in that can be swapped for real auth later without changing the domain model.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A FastAPI dependency resolves the current user from a request header (e.g. X-User-Id) against the User table, returning 401 if the header is missing or names a nonexistent user
- [ ] #2 Endpoints can require a minimum role (e.g. admin) via this dependency and reject insufficient roles with 403
- [ ] #3 The frontend has a current-user switcher (a dropdown of known users) that sets the header on every API request
- [ ] #4 Backend and frontend unit tests cover the dependency's allow/deny cases and the switcher setting the header correctly
<!-- AC:END -->
