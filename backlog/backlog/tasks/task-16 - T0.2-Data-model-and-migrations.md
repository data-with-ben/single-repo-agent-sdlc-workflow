---
id: TASK-16
title: T0.2 Data model and migrations
status: To Do
assignee: []
created_date: '2026-07-03 15:25'
labels:
  - foundation data
dependencies:
  - TASK-15
priority: high
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the entities defined in SPEC.md Section 4 (domain data model) as schema plus migrations. SPEC.md is the source of truth for exact fields and relationships; reference it directly once added to backlog docs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All entities exist with the fields specified in SPEC.md Section 4
- [ ] #2 Migrations run clean from an empty database
- [ ] #3 A documented ER description or diagram is generated
- [ ] #4 Foreign keys are enforced (e.g. Assignment to User/Client, TimeEntry to User/Client)
<!-- AC:END -->
