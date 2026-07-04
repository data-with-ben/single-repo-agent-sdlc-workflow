---
id: TASK-23
title: T2.2 Team scoring and game resolution
status: To Do
assignee: []
created_date: '2026-07-03 15:26'
updated_date: '2026-07-04 01:08'
labels:
  - backend scoring
dependencies:
  - TASK-22
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
priority: high
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Given ObjectiveResults, team membership, and the schedule, compute normalized team scores, the team bonus, and win/loss per SPEC.md Section 7.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Per-member score normalization is correct
- [ ] #2 A test demonstrates fairness between a 3-member team and a 5-member team
- [ ] #3 The team bonus is applied only when all present members hit the 11am objective
- [ ] #4 Draw handling is implemented per the resolved open decision in SPEC.md Section 11.1
- [ ] #5 Byes are handled without affecting other teams' scores
<!-- AC:END -->
