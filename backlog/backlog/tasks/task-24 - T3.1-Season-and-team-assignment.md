---
id: TASK-24
title: T3.1 Season and team assignment
status: To Do
assignee: []
created_date: '2026-07-03 15:26'
labels:
  - backend
dependencies:
  - TASK-23
priority: medium
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create seasons and randomly partition active consultants into teams of 3-5 members, reshuffling teams when a new season starts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Teams are within the 3-5 member size bounds
- [ ] #2 Team assignment is random but every active consultant is placed on a team
- [ ] #3 Reshuffling at a new season produces different teams
- [ ] #4 Season lifecycle (upcoming, active, complete) is enforced
<!-- AC:END -->
