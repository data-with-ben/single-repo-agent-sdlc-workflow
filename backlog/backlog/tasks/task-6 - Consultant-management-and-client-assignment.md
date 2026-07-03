---
id: TASK-6
title: Consultant management and client assignment
status: To Do
assignee: []
created_date: '2026-07-03 13:28'
updated_date: '2026-07-03 15:24'
labels:
  - backend frontend
  - flagged-for-removal
dependencies:
  - TASK-5
priority: high
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Managers add consultants to the system and assign them to the clients they work with. This assignment is what determines which client a consultant logs time against.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A manager or super admin can add a new consultant
- [ ] #2 A manager or super admin can assign a consultant to one or more clients
- [ ] #3 A manager or super admin can remove a consultant's assignment from a client
- [ ] #4 A consultant cannot add other consultants or change client assignments
- [ ] #5 A consultant can view the list of clients they are currently assigned to
- [ ] #6 Frontend provides a consultant list view and, for managers, assignment controls
- [ ] #7 Backend and frontend unit tests cover assignment, unassignment, and the consultant restriction
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
