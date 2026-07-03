---
id: TASK-8
title: Manager team timesheet review view
status: To Do
assignee: []
created_date: '2026-07-03 13:29'
updated_date: '2026-07-03 15:24'
labels:
  - backend frontend
  - flagged-for-removal
dependencies:
  - TASK-7
priority: medium
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Managers need a rollup across all consultants on their clients to see who has and hasn't logged time, without opening each consultant's calendar individually.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A manager can view a table of all consultants assigned to their clients with each day's submission status for a selected week
- [ ] #2 A manager can filter the view by client
- [ ] #3 A super admin can view this rollup across all clients, not just a subset
- [ ] #4 A consultant cannot access this rollup view
- [ ] #5 Backend and frontend unit tests cover the rollup query and the consultant access restriction
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
