---
id: TASK-39
title: Apply a dark-theme design system across the app
status: To Do
assignee: []
created_date: '2026-07-06 03:12'
labels: []
dependencies: []
priority: high
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The app currently has zero styling -- every component (WeeklyCalendar, MorningProjection, Scoreboard, Portfolio, Brackets, ClientAdmin, UserSwitcher) renders as plain unstyled HTML with only occasional inline style for basic layout (flex gaps, a selection border). SPEC.md never specifies a design system, but the five wireframe reference images in backlog/backlog/assets/wireframes/ (games-view.png, consultant-view.png, consultant-view-2.png, admin-view-1.png, drafting-view.png) all consistently depict a dark-theme, card-based dashboard aesthetic. This task applies that inferred style guide as the app's default (and only, for now) theme.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A shared style foundation exists (global CSS / theme file) applied app-wide via a single import, not per-component ad hoc styles
- [ ] #2 Dark theme is the default: near-black page background, card panels in a slightly lighter dark gray with a subtle 1px border and rounded corners, matching the wireframes
- [ ] #3 Semantic colors match the wireframes: blue accent for selection/links/badges (e.g. current-user pill, selected client row, today marker), green for positive/on-time/success states, red for negative/risky/missing states, amber/orange for in-progress/warning/late states
- [ ] #4 Primary actions use a solid high-contrast pill button (e.g. Submit entry, Draft Priya); secondary actions use an outlined ghost pill button (e.g. + Add client, Assign)
- [ ] #5 Headings are bold and legible against the dark background; secondary/meta text (timestamps, hints) uses a muted gray, matching the wireframes' text hierarchy
- [ ] #6 Every existing screen (weekly calendar, morning projection, scoreboard/box score, clients and assignments, portfolio/exchange, brackets) is restyled consistently -- no screen is left in the old unstyled state
- [ ] #7 Existing frontend unit tests continue to pass (queries by role/label/text, not by removed default styling)
<!-- AC:END -->
