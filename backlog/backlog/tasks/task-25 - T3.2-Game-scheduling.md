---
id: TASK-25
title: T3.2 Game scheduling
status: To Do
assignee: []
created_date: '2026-07-03 15:27'
labels:
  - backend
dependencies:
  - TASK-24
priority: medium
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generate the season's game schedule as a round-robin, one matchup set per workday, with byes for odd team counts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every team plays a balanced schedule across the season
- [ ] #2 No team is double-booked on the same date
- [ ] #3 Byes are recorded for any team without a matchup on a given workday
<!-- AC:END -->
