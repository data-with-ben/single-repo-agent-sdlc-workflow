---
id: TASK-3
title: User registration and login
status: To Do
assignee: []
created_date: '2026-07-03 13:28'
updated_date: '2026-07-03 15:24'
labels:
  - backend frontend auth
  - flagged-for-removal
dependencies:
  - TASK-2
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Users need individual accounts before any protected feature can exist. Registration creates an account with a role and a timezone (needed later for timezone-aware scoring); login issues a session/token used by all later access-control work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A new user can register with email, password, a role, and an IANA timezone
- [ ] #2 A registered user can log in with correct credentials and receive a valid session/token
- [ ] #3 Login fails with a clear invalid-credentials error for a wrong password or unknown email
- [ ] #4 Passwords are stored hashed, never in plaintext
- [ ] #5 Backend unit tests cover successful registration, successful login, and failed login
- [ ] #6 Frontend has a login and registration form that calls these endpoints and shows success and error states
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-07-03 15:24
---
FLAGGED FOR REMOVAL: Superseded by the new, more detailed T0-T5 'Fantasy Timesheets' backlog (objective engine, pricing/market mechanics, seasons/games) that replaces this earlier draft-and-trade design. Flagged 2026-07-03. Eligible for sweep on or after 2026-07-17.
---
<!-- COMMENTS:END -->
