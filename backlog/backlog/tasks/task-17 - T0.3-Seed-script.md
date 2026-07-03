---
id: TASK-17
title: T0.3 Seed script
status: To Do
assignee: []
created_date: '2026-07-03 15:25'
labels:
  - foundation data
dependencies:
  - TASK-16
priority: high
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Seed clients, roughly 15 consultants with varied punctuality profiles (e.g. always by 11am, chronic late, streaky), one active season with random teams, and empty portfolios/wallets with a starting balance. This is what makes every later screen and the nightly job exercisable during development.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Running the seed script against an empty database produces data sufficient to exercise every screen and the nightly job
- [ ] #2 Seeded consultants have varied, clearly distinguishable punctuality profiles
- [ ] #3 Re-running the seed script is idempotent or clearly resets prior seed data
<!-- AC:END -->
