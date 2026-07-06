---
id: TASK-40
title: Replace dev-mode X-User-Id auth with real authentication
status: To Do
assignee: []
created_date: '2026-07-06 03:12'
labels: []
dependencies: []
priority: medium
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
task-35 introduced a deliberate stand-in: the caller's identity is resolved from a plain X-User-Id request header against the User table, with a frontend dropdown switcher to set it -- explicitly documented as out of scope for real auth per SPEC.md's non-goals (a local/demo-scale game), but built so it could be swapped later without changing the domain model. This task replaces that stand-in with real authentication (e.g. hashed-password login or an OAuth/OIDC provider, session or JWT based) so identity can no longer be spoofed by simply setting a header.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Users authenticate with real credentials (password or third-party identity provider) rather than picking themselves from an open dropdown
- [ ] #2 get_current_user and require_role in backend/app/auth.py are replaced or reimplemented against the new auth mechanism without changing their call sites (every existing endpoint using Depends(get_current_user)/Depends(require_role(...)) continues to work unmodified)
- [ ] #3 Sessions/tokens expire and can be invalidated (logout works)
- [ ] #4 The frontend UserSwitcher dev tool is removed or gated to non-production use only
- [ ] #5 Existing backend and frontend auth tests are updated to cover the new mechanism's allow/deny cases
<!-- AC:END -->
