---
id: TASK-9
title: Draftable consultants and roster drafting
status: To Do
assignee: []
created_date: '2026-07-03 13:29'
updated_date: '2026-07-03 15:24'
labels:
  - backend frontend fantasy
  - flagged-for-removal
dependencies:
  - TASK-6
priority: medium
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Introduces the fantasy layer: every consultant is a draftable entity. Any authenticated user can draft consultants onto a personal roster, similar to a fantasy sports draft. This roster is what fantasy points will later be attributed to.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Any authenticated user can view the pool of draftable consultants and which, if any, are already drafted
- [ ] #2 A user can draft an undrafted consultant onto their own roster
- [ ] #3 A consultant cannot be drafted onto more than one user's roster at the same time
- [ ] #4 A user can view their current roster of drafted consultants
- [ ] #5 Frontend provides a draft screen showing the available pool and the user's current roster
- [ ] #6 Backend and frontend unit tests cover drafting, the already-drafted restriction, and roster viewing
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
