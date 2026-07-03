---
id: TASK-12
title: Consultant trading between rosters
status: To Do
assignee: []
created_date: '2026-07-03 13:30'
updated_date: '2026-07-03 15:24'
labels:
  - backend frontend fantasy
  - flagged-for-removal
dependencies:
  - TASK-9
priority: medium
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lets users trade drafted consultants with each other, similar to a fantasy sports trade, with a deadline that blocks trades close to the end of a scoring period so no one can dump an underperforming consultant right before a bad stretch.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A user can propose a trade of one of their rostered consultants to another user, optionally requesting a consultant back in return
- [ ] #2 The receiving user can accept or reject a proposed trade
- [ ] #3 An accepted trade moves the consultant(s) to their new roster(s) immediately
- [ ] #4 A trade cannot be proposed or accepted after the configured trade deadline for the current scoring period
- [ ] #5 A user cannot trade a consultant they do not currently have rostered
- [ ] #6 Backend and frontend unit tests cover propose, accept, reject, and the deadline restriction
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
