---
id: TASK-22
title: T2.1 Objective engine module (pure)
status: Done
assignee:
  - '@agent'
created_date: '2026-07-03 15:26'
updated_date: '2026-07-05 02:40'
labels:
  - backend scoring
dependencies:
  - TASK-19
references:
  - feature/task-22-objective-engine
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
modified_files:
  - backend/app/objective_engine.py
  - backend/tests/test_objective_engine.py
  - backend/pyproject.toml
  - .gitignore
  - backlog/backlog/tasks/task-22 - T2.1-Objective-engine-module-pure.md
priority: high
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A pure function (TimeEntry[], date, ptoCalendar) -> ObjectiveResult[] implementing all scoring rules from SPEC.md Section 6, with no I/O. This and the pricing module (T4.1) are the two highest-value, most heavily tested units in the system.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Returns correct per-consultant results for projected-by-11, logged-same-day, EOD, and perfect-day objectives, with points totals capped at 30
- [x] #2 Respects PTO exclusion and the no-assigned-work-means-neutral rule
- [x] #3 Reads only transition timestamps, never mutable state
- [x] #4 Achieves at least 90% branch coverage with table-driven tests
- [x] #5 Tests cover edge cases: exactly 11:00, a description just under and just over the minimum length, mixed multi-client days, and all-PTO days
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. New module backend/app/objective_engine.py with a compute_objective_results(entries: list[TimeEntry], game_date: date, pto_consultant_ids: set[int]) -> list[ObjectiveResult] pure function, matching the exact signature named in SPEC.md Section 10 (Architecture notes), and a plain dataclass ObjectiveResult (consultant_id, game_date, projected_by_11, logged_same_day, eod_update, perfect_day, points) -- omitting id (persistence-only, no I/O here) and team_id (assigned later by the not-yet-built team-scoring layer, task-23, per the architecture notes ordering: objective engine -> team scoring -> game winners).
2. Resolving an explicitly open spec question (Section 11, item 5: definition of a working slot is unresolved org policy): this plan treats each TimeEntry in the input list, for a given consultant on game_date, as one working slot. The functions signature takes TimeEntry[] directly with no separate Assignment[] parameter, so the caller (the not-yet-built nightly reveal job, task-26) is responsible for constructing the input list to include one entry per client a consultant should have worked that day (including still-empty entries for untouched assignments) -- this function only aggregates over whatever entries it is given per consultant. A consultant with zero entries in the input for game_date is neutral (no assigned work) and is omitted entirely from the returned list, satisfying AC #2s no-assigned-work-means-neutral rule without needing Assignment data. This interpretation is flagged explicitly for hostile plan review to challenge, since Section 11 marks it as genuinely open.
3. PTO exclusion (AC #2): any consultant_id present in pto_consultant_ids is omitted entirely from the output, checked before the no-assigned-work check (independent of whether they happen to have entries) -- ptoCalendar is passed in by the caller since this function has no I/O and cannot query User.status itself; scoped to a single set of IDs for the one game_date being scored, not a multi-date calendar structure, since the function only ever scores one date per call.
4. Per-consultant objective derivation, reading only projected_at/logged_at/updated_at/description -- never entry.state (AC #3s anti-gaming requirement, since state is a cached convenience field per timeentry.pys own docstring and must not be trusted):
   - projected_by_11: every slot has projected_at set, its date equals game_date, and its time is at or before 11:00 (inclusive, matching SPEC.md Sections <= 11:00 wording).
   - logged_same_day: every slot has logged_at set and its date equals game_date (no time-of-day cutoff, matching SPEC.md Section 5 loggedAt is on workDate).
   - eod_update: every slot has updated_at set, its date equals game_date, its time is at or after 15:00 (inclusive), and its description is non-null with length at least 20 chars (matching the same default already used in WeeklyCalendar.tsx/MorningProjection.tsx). Treated as an every-slot requirement for consistency with the other two objectives and the aggregated across the days entries framing at the top of Section 6, even though the table row for this one is slightly less explicit about every slot than the other two rows -- flagged for hostile review as an interpretation, not a certainty.
   - perfect_day: all three of the above true for that consultant.
   - points: 10 + 10 + 5 + 5 for each true objective respectively, capped at min(total, 30) per AC #1s exact wording (the cap is mathematically redundant given the fixed point values sum to exactly 30, but implemented explicitly to satisfy the AC as written).
5. Local time zone (AC #1, #5): no per-user timezone is stored or passed to this function (a known, already-documented gap from task-17, deferred). All comparisons are made directly against the timestamps own UTC values (naive datetimes that are true UTC instants throughout this backend, confirmed during task-21). This is a documented simplification consistent with the same class of simplification already used in WeeklyCalendar.tsx/MorningProjection.tsx (browser local clock as a stand-in), applied here as UTC-as-local pending a real per-user timezone field.
6. Table-driven tests (test_objective_engine.py) covering AC #4 (>=90% branch coverage) and AC #5s named edge cases: exactly 11:00 (boundary inclusive), a description at 19 vs 20 chars (just under/over minimum), a mixed multi-client day (one client meeting all objectives, another missing one, expecting the day-level objective to fail since one slot fails), an all-PTO date (pto_consultant_ids covers every consultant with entries, expecting an empty result list), a no-assigned-work consultant (zero entries for game_date, expecting omission), and a state-is-empty-but-timestamps-populated case proving AC #3 (state field is never read).
7. Verification pass: run pytest with coverage (pytest-cov or manual branch inspection since pyproject.toml does not currently list pytest-cov -- check before assuming it is available) and ruff.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (3 warning(s), 1 minor)

- Warning: the plans core design decision -- treating each input TimeEntry as one working slot -- directly resolves an explicitly open spec question (SPEC.md Section 11, item 5: definition of a working slot is unresolved org policy). The interpretation is well-grounded (matches the exact function signature SPEC.md itself names, with no Assignment[] parameter, and does not invent new I/O), but should be revisited once actual org policy is decided. Not blocking now since it is the most directly implementable, spec-consistent reading.
- Warning: pytest-cov (or an equivalent way to actually measure branch coverage) is not currently a dependency in pyproject.toml (confirmed via grep). AC #4 requires a specific coverage number -- table-driven tests alone do not verify this without a measurement tool. Must be added (or an alternative method used) during implementation, not just asserted.
- Warning: the plan does not explicitly state whether input entries are assumed pre-filtered to game_date by the caller, or must be defensively filtered within the function itself. This should be resolved explicitly and documented during implementation, since it affects how a mixed multi-client days test is constructed and what the function guarantees to callers.
- Minor: TimeEntry.work_date is a datetime column but game_date is a date parameter -- the plan does not spell out the .date() conversion needed to compare them, though this is a standard, low-risk pattern already used elsewhere in this codebase (_serialize_entry).

IMPLEMENTATION SUMMARY

What was implemented:
- backend/app/objective_engine.py (new): compute_objective_results(entries, game_date, pto_consultant_ids) -> list[ObjectiveResult], a pure function with no I/O implementing SPEC.md Section 6 scoring. Also defines the ObjectiveResult dataclass (consultant_id, game_date, projected_by_11, logged_same_day, eod_update, perfect_day, points) -- omitting id (persistence-only) and team_id (attached later by the not-yet-built team-scoring layer, task-23).
- backend/tests/test_objective_engine.py (new): 28 table-driven tests (pytest.mark.parametrize for the points-cap matrix) covering every AC #5 edge case plus extras (no-assigned-work, mixed dates in the input list).
- backend/pyproject.toml: added pytest-cov>=6.0.0 as a dev dependency -- needed to actually measure the >=90% branch coverage AC #4 requires, since no coverage tool existed in this repo before.
- .gitignore: added .coverage (the coverage.py cache file pytest-cov generates), since it is a regenerable local artifact, not evidence to commit.

Key technical decisions:
- Working slot definition: SPEC.md Section 11 (Open decisions), item 5, explicitly leaves definition of a working slot as unresolved org policy. This implementation treats each TimeEntry given to the function, for a consultant on game_date, as one working slot -- the functions signature (TimeEntry[], date, ptoCalendar) has no Assignment[] parameter, so the caller (the not-yet-built nightly reveal job, task-26) is responsible for constructing the input list to include one entry per client a consultant should have worked that day, including still-empty entries for untouched assignments. Flagged during hostile plan review as an interpretation to revisit once actual org policy is decided, not a certainty.
- Entries are defensively filtered to game_date inside the function (entry.work_date.date() != game_date are skipped) rather than trusting the caller to pre-filter -- resolves a gap hostile plan review flagged, and is covered by TestEntriesFilteredToGameDate.
- EOD update is treated as an every-slot requirement (like the other two objectives), for consistency with the aggregated across the days entries framing at the top of Section 6, even though that particular table row is slightly less explicit about every slot than the other two rows. Flagged during hostile review as an interpretation.
- No per-user timezone is stored or passed to this function (a known, already-documented gap from task-17/task-20/task-21). All time-of-day comparisons are made directly against the timestamps own values -- naive datetimes that are true UTC instants throughout this backend (confirmed during task-21s Z-suffix fix) -- effectively UTC-as-local, the same class of simplification already used in WeeklyCalendar.tsx/MorningProjection.tsx.
- Anti-gaming (AC #3): the implementation reads only projected_at/logged_at/updated_at/description; entry.state is referenced nowhere in executable code (confirmed via grep -- the only match is in the modules own docstring). Proven by a dedicated test constructing an entry with state=empty but full timestamps (scores correctly) and one with state=updated but no timestamps (scores zero).

Integration points:
- No integration with existing endpoints yet -- this module is not wired into main.py or any route. Per the architecture notes (SPEC.md Section 10), it is meant to be called by the nightly reveal job (task-26), which does not exist yet. This is a self-contained, importable module only.
- New dev-only dependency: pytest-cov. No production dependencies added.

Testing coverage:
- 66 backend pytest passed (38 existing + 28 new), ruff clean.
- 100% branch coverage measured directly via pytest --cov=app.objective_engine --cov-branch (AC #4 requires >=90%).
- All AC #5 edge cases covered: exactly 11:00 (inclusive boundary) and one second past, description at 19 vs 20 chars, a mixed multi-client day (one slot failing an objective fails the whole days objective for that consultant), and an all-PTO date (every consultant with entries excluded, empty result list).
- E2E: skipped -- this is a pure backend module with no I/O, no API endpoint, and no UI surface to exercise in a browser.

Future considerations:
- Once task-23 (team scoring) is built, it will need to attach team_id to these results and implement the team bonus (+10 for whole team projected by 11am) and normalization -- explicitly out of this tasks scope per the architecture notes ordering (objective engine -> team scoring -> game winners).
- Once task-26 (nightly reveal job) is built, it becomes the actual caller responsible for constructing the TimeEntry[] input (including empty entries for untouched assignments) and the pto_consultant_ids set (likely derived from User.status == pto for the given date) -- this task does not implement that caller.
- The working-slot and every-slot-for-EOD interpretations documented above should be revisited if/when SPEC.md Section 11s open decisions are formally resolved.

CODE REVIEW: Approved with 1 minor suggestion (fixed).

No critical or major issues found. Code is clean, well-organized, DRY (shared _on_date_by_cutoff helper reused between projected_by_11 and eod_update), and directly matches the design decisions documented in the plan and Implementation Notes. Anti-gaming requirement (AC #3) verified by direct source inspection: entry.state appears nowhere in executable code, only in the module docstring.

Fixed during review: _on_date_by_cutoff was missing a type hint on its ts parameter (datetime | None) -- added for consistency with the rest of the modules full type-hint discipline and the codebases existing conventions (e.g. timeentry.py). Re-ran full suite after the fix: 66 passed, ruff clean.

Minor, non-blocking: the at_or_before boolean flag toggling between <= and >= comparisons in _on_date_by_cutoff is a little compact/clever; splitting into two named helpers would read slightly more directly, but the current version is well-tested (100% branch coverage) and the docstring/naming make the intent clear -- a style preference, not a correctness concern.

Requirements alignment: all 5 ACs verified against real test runs and direct coverage measurement (100% branch coverage, well above the 90% threshold). No scope creep -- team scoring, dividends, and market mechanics from later spec sections are correctly left untouched. No security issues (pure function, no I/O, no external input parsing). New dependency (pytest-cov) is dev-only and directly required to verify AC #4 numerically.
<!-- SECTION:NOTES:END -->
