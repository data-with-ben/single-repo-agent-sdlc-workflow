---
id: TASK-25
title: T3.2 Game scheduling
status: Done
assignee:
  - '@agent'
created_date: '2026-07-03 15:27'
updated_date: '2026-07-05 03:36'
labels:
  - backend
dependencies:
  - TASK-24
references:
  - feature/task-25-game-scheduling
modified_files:
  - .gitignore
  - backend/pyproject.toml
  - backend/app/game_scheduling.py
  - backend/app/season.py
  - backend/tests/test_game_scheduling.py
  - backend/tests/test_season.py
  - backlog/backlog/tasks/task-25 - T3.2-Game-scheduling.md
priority: medium
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Generate the season's game schedule as a round-robin, one matchup set per workday, with byes for odd team counts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every team plays a balanced schedule across the season
- [x] #2 No team is double-booked on the same date
- [x] #3 Byes are recorded for any team without a matchup on a given workday
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-25 (T3.2 Game scheduling):

This branch depends on task-24 (Season/Team creation and assignment), whose branch
is not yet merged into main. Per the established duplicate-across-branches pattern
(used for CORS, objective_engine, pytest-cov, and again for task-37), backend/app/
season.py and its test file are ported verbatim onto this branch from
feature/task-24-season-team-assignment, alongside the corresponding pyproject.toml
(pytest-cov) and .gitignore (.coverage) entries. The Season/Team/TeamMembership/Game
SQLAlchemy models already exist in baseline app/models.py (not task-24-specific), so
no model changes are needed.

New module: backend/app/game_scheduling.py -- a pure function plus a thin DB-writing
wrapper, following the same shape as objective_engine.py (pure) and team_scoring.py
(pure), both of which this module sits alongside in the pipeline.

1. Workday enumeration: reuse the existing Mon-Fri convention already established in
   app/seed.py's _last_n_workdays (cursor.weekday() < 5), applied here to walk forward
   from season.start_date to season.end_date inclusive, producing the ordered list of
   workdays that need a matchup set.

2. Round-robin pairing (circle method): given the season's teams (ordered by id for
   determinism), generate the standard round-robin round sequence:
   - If the team count is odd, add a sentinel bye slot to make it even.
   - Fix the first team, rotate the rest around it each round, producing team_count-1
     (or team_count, if a sentinel was added) rounds where every real team is paired
     with every other real team exactly once, and is paired with the bye slot exactly
     once if the count is odd.
   - Whichever team is paired with the bye slot in a given round is that round's bye
     team; it produces no Game row for that round.

3. Schedule assignment: map the round sequence onto the season's workdays in order,
   cycling back to round 0 once the round sequence is exhausted (double round-robin
   naturally happens if the season is long enough to need 2x the base cycle; the
   cycle is not manually reversed for home/away, since the models track home/away
   only for db bookkeeping, and SPEC.md doesn't call out home/away advantage anywhere
   in scoring -- normalized per-present-member score is symmetric). This directly
   satisfies AC #1 (every team appears in exactly one game, or is the bye, every
   single workday -- so games played only diverges by at most 1 across teams if the
   season length isn't an exact multiple of the round length, which is the maximum
   achievable balance for an odd total working-day count) and AC #2 (round-robin's
   circle method guarantees each team appears in at most one pairing per round by
   construction, so no team can be double-booked -- verified by an explicit assertion
   in the implementation, not just relied upon from the algorithm's math).

4. Bye recording (AC #3): since app.models.Game has non-nullable home_team_id and
   away_team_id (no schema support for a one-sided bye row), and team_scoring.py's
   own docstring already documents the resolved interpretation that byes are the
   *absence* of a Game row for that team/date (a team's bye is inferred downstream,
   not stored as a special Game row) -- this task follows that same interpretation
   for consistency with the already-built downstream consumer. The scheduling
   function returns byes as an explicit `{date: bye_team_id}` mapping alongside the
   list of games to create, so callers (and tests) can assert on byes directly rather
   than only by absence. This is a plan deviation worth flagging explicitly during
   implementation if it turns out the hostile review or later steps want byes
   persisted as actual DB rows instead -- noting it up front here.

5. DB-writing wrapper: `schedule_season_games(db, season)` calls the pure
   `_round_robin_schedule(team_ids, workdays)` function, then creates Game rows
   (state set to scheduled, revealed=False, home_score/away_score=None) for every
   non-bye pairing, and returns (created_games, byes_by_date) for the caller/tests
   to inspect. Matches season.py's pattern of pure-computation-plus-thin-DB-wrapper
   already used in this module in this codebase.

6. Tests: a pure-function test suite mirroring test_objective_engine.py /
   test_season.py's style -- table-driven / parametrized round-robin correctness
   checks across a range of team counts (even and odd, small and large), asserting:
   no team appears twice in the same round's pairings, every team eventually plays
   every other team when the schedule runs a full cycle, byes rotate across all
   odd-count teams rather than always landing on the same team, and the DB-writing
   wrapper produces the correct count of Game rows and correctly excludes byes from
   them while still surfacing byes in its return value.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (2 warnings, 2 minor): (1) plan must specify behavior for seasons with fewer than 2 teams -- raise ValueError, matching season.py precedent; (2) plan must specify re-run/idempotency behavior -- delete existing games for the season before regenerating, matching assign_teams reassignment precedent; (3) balanced-schedule interpretation (max spread of 1 game when season length is not an exact multiple of the round-robin cycle) should be stated explicitly in implementation notes; (4) season.end_date should be treated as inclusive -- document this assumption.

E2E TESTS: Skipped -- backend-only pure scheduling module (game_scheduling.py), no HTTP endpoint or UI surface introduced, matching the same rationale as season.py (task-24), objective_engine.py (task-22), and team_scoring.py (task-23).

IMPLEMENTATION NOTES: Added backend/app/game_scheduling.py (pure build_schedule function plus a thin DB-writing schedule_season_games wrapper, following the same shape as season.py/objective_engine.py/team_scoring.py). Ported season.py + its test from task-24's branch (built from main, since task-24 is not yet merged and this workflow has no auto-merge step -- same duplicate-across-branches pattern used repeatedly this session), plus its pyproject.toml (pytest-cov) and .gitignore (.coverage) changes. Algorithm: standard round-robin circle method, padding an odd team count with a sentinel bye slot; the round sequence cycles across the season's Mon-Fri workdays (reusing app.seed's existing weekday-less-than-5 convention). Addressed all 4 hostile-review findings: (1) fewer than 2 teams raises ValueError; (2) schedule_season_games deletes any previously-scheduled games for the season before regenerating, so re-running is idempotent; (3) balance is exact after any whole number of cycles and differs by at most 1 game otherwise -- documented in the module docstring and verified by test_uneven_season_length_differs_by_at_most_one_game; (4) season.end_date is treated as inclusive, documented in the module docstring. Byes are recorded as an explicit {date: team_id} return value (not a DB row, since Game.home_team_id/away_team_id are non-nullable) -- consistent with team_scoring.py's already-documented bye interpretation. Tests: 37 new (parametrized across team counts 2-12 for no-double-booking and full-cycle-coverage, plus season-integration tests for schedule_season_games). Full backend suite: 134 passed. Ruff clean.

CODE REVIEW: Approved with 1 minor fix applied -- tightened _round_robin_rounds' internal ids type hint to list[int | None] to correctly reflect the sentinel bye value, rather than the misleading list[int]. Ruff clean, all 37 new + 97 existing backend tests pass.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-skip, notes, code-review, this audit).
<!-- SECTION:NOTES:END -->
