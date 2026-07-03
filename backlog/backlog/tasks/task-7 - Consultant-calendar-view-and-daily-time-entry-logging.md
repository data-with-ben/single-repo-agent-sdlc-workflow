---
id: TASK-7
title: Consultant calendar view and daily time entry logging
status: To Do
assignee: []
created_date: '2026-07-03 13:29'
updated_date: '2026-07-03 15:24'
labels:
  - backend frontend
  - flagged-for-removal
dependencies:
  - TASK-6
priority: high
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The core timesheet feature: a consultant sees a calendar of their days and logs hours plus a description for each day against one of their assigned clients. The exact submission timestamp captured here is what the fantasy scoring engine will later read.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A consultant sees a calendar view showing which days already have a time entry and which do not
- [ ] #2 A consultant can add a time entry for a day with hours worked, a description, and one of their assigned clients
- [ ] #3 A consultant can edit or delete their own time entry before it is locked by a season/scoring cutoff
- [ ] #4 A consultant cannot log a time entry against a client they are not assigned to
- [ ] #5 A manager or super admin can view a consultant's calendar and entries in read-only form
- [ ] #6 Backend and frontend unit tests cover creating, editing, deleting, and the client-assignment restriction
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
