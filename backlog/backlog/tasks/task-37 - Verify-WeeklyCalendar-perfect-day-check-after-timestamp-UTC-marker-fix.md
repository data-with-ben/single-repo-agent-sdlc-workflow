---
id: TASK-37
title: Verify WeeklyCalendar perfect-day check after timestamp UTC-marker fix
status: To Do
assignee: []
created_date: '2026-07-05 02:22'
labels:
  - backend frontend bug
dependencies: []
references:
  - feature/task-21-morning-project-day
  - feature/task-20-weekly-calendar-day-entry
priority: high
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
task-21 found and fixed a real bug in backend _serialize_entry: projected_at/logged_at/updated_at/first_submitted_at were serialized via Python isoformat() with no Z suffix or UTC offset, even though they always represent true UTC instants. Verified empirically that a spec-compliant JS engine parses a Z-less timestamp as local time, not UTC -- a full timezone-offset misread (e.g. 4 hours in EDT) that can even flip which calendar day an event is attributed to near midnight. The fix (append Z at serialization) landed on task-21s branch (feature/task-21-morning-project-day, not yet merged to main). WeeklyCalendar.tsx (task-20, feature/task-20-weekly-calendar-day-entry, also not yet merged) has an identical projected_at-based perfect-day check (computeLivePointsHint in WeeklyCalendar.tsx) that reads the same unmarked timestamp format and is very likely affected by the same bug. This was not verified directly since task-20 is already Done/pushed and was not reopened for this fix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Confirm whether WeeklyCalendars perfect-day check (computeLivePointsHint) produces the correct result once both task-20 and task-21s branches are merged together (the fix landing via task-21 should resolve it for free, since both read the same backend-serialized field)
- [ ] #2 If any other frontend code introduced after task-21 parses projected_at/logged_at/updated_at/first_submitted_at via new Date(), confirm it is not relying on the old (unmarked, mis-parsed-as-local) behavior
- [ ] #3 Add a regression test in WeeklyCalendar.test.tsx (or wherever the merged code lands) that pins a UTC-marked timestamp via a fixed system clock and asserts the perfect-day bonus is computed using the correct local hour, not a timezone-shifted one
<!-- AC:END -->
