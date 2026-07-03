---
id: TASK-2
title: 'Data models for users, clients, consultant assignments, and time entries'
status: To Do
assignee: []
created_date: '2026-07-03 13:28'
updated_date: '2026-07-03 15:24'
labels:
  - backend data
  - flagged-for-removal
dependencies: []
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Foundational persistence layer for the consultancy timesheet app: users (with a role of super_admin, manager, or consultant), clients, the assignment of consultants to clients, and time entries a consultant logs against a client for a given day.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Backend persists User records with a role of super_admin, manager, or consultant
- [ ] #2 Backend persists Client records
- [ ] #3 Backend persists an assignment linking a consultant to a client, with a consultant assignable to more than one client
- [ ] #4 Backend persists TimeEntry records linking a consultant, a client, a work date, hours, a description, and the timestamp the entry was actually submitted
- [ ] #5 Data persists across backend restarts (not held only in memory)
- [ ] #6 Backend unit tests cover model creation and relationships for all entities
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
