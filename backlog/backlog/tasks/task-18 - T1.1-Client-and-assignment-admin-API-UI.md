---
id: TASK-18
title: T1.1 Client and assignment admin (API + UI)
status: To Do
assignee: []
created_date: '2026-07-03 15:25'
labels:
  - backend frontend
dependencies:
  - TASK-17
priority: high
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CRUD for clients, and the ability to assign or unassign consultants to clients. This determines which clients a consultant can log time against downstream. UI should match wireframe 3 once that reference image is attached to this task's assets.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An admin can create and archive a client
- [ ] #2 An admin can assign and remove a consultant from a client
- [ ] #3 A consultant's assignments determine the client options returned for time entry
- [ ] #4 Non-admins cannot mutate clients or assignments
- [ ] #5 The UI matches the layout described for wireframe 3 (client list with assignment controls)
<!-- AC:END -->
