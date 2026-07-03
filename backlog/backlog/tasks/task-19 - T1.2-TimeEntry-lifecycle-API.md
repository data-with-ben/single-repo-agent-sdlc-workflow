---
id: TASK-19
title: T1.2 TimeEntry lifecycle (API)
status: To Do
assignee: []
created_date: '2026-07-03 15:25'
labels:
  - backend
dependencies:
  - TASK-18
priority: high
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the TimeEntry state machine from SPEC.md Section 5: project(), log(), and eodUpdate(), with correct timestamp writes and an immutable firstSubmittedAt used later by the anti-gaming objective rules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each state transition (project, log, eodUpdate) writes exactly the fields specified in SPEC.md Section 5
- [ ] #2 firstSubmittedAt is written once on first submission and never changes afterward
- [ ] #3 Illegal transitions are rejected with a clear error
- [ ] #4 Multiple entries per (consultant, workDate) are supported
- [ ] #5 Unit tests cover each transition and the anti-gaming invariant: a later fix to an entry does not backdate its scoring objective
<!-- AC:END -->
