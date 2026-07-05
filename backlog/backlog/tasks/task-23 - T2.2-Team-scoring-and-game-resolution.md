---
id: TASK-23
title: T2.2 Team scoring and game resolution
status: Done
assignee:
  - '@agent'
created_date: '2026-07-03 15:26'
updated_date: '2026-07-05 02:56'
labels:
  - backend scoring
dependencies:
  - TASK-22
references:
  - feature/task-23-team-scoring
documentation:
  - docs/doc-1 - Fantasy-Timesheets-—-Product-Technical-Spec.md
modified_files:
  - backend/app/objective_engine.py
  - backend/app/team_scoring.py
  - backend/tests/test_objective_engine.py
  - backend/tests/test_team_scoring.py
  - backend/pyproject.toml
  - .gitignore
  - backlog/backlog/tasks/task-23 - T2.2-Team-scoring-and-game-resolution.md
priority: high
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Given ObjectiveResults, team membership, and the schedule, compute normalized team scores, the team bonus, and win/loss per SPEC.md Section 7.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Per-member score normalization is correct
- [x] #2 A test demonstrates fairness between a 3-member team and a 5-member team
- [x] #3 The team bonus is applied only when all present members hit the 11am objective
- [x] #4 Draw handling is implemented per the resolved open decision in SPEC.md Section 11.1
- [x] #5 Byes are handled without affecting other teams' scores
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Duplicate task-22s backend/app/objective_engine.py (ObjectiveResult dataclass + compute_objective_results) onto this branch -- task-23 depends on task-22, which is Done in the backlog but not yet merged into main, so this branch does not have that code yet. Same accepted, already-documented pattern used across task-20/task-1/task-21 for exactly this reason (dependency task done but unmerged); expected to collapse into one copy whenever these branches merge.
2. New module backend/app/team_scoring.py with a resolve_games(objective_results: list[ObjectiveResult], team_memberships: dict[int, set[int]], games: list[Game]) -> list[GameResult] pure function, no I/O, continuing the same pipeline stage SPEC.md Section 10 names (objective engine -> team scoring -> game winners), still before the write results step owned by the not-yet-built nightly reveal job (task-26). Uses real app.models.Game instances directly as input (matching the established codebase precedent of pure functions accepting real SQLAlchemy model instances -- timeentry.py, objective_engine.py -- rather than inventing parallel dataclasses), constructed in-memory for tests with no DB.
3. New GameResult dataclass: game_id, home_team_id, away_team_id, home_score (float | None), away_score (float | None), home_bonus_applied (bool), away_bonus_applied (bool), winner_team_id (int | None), is_draw (bool), postponed (bool). Kept distinct from the already-existing, separately-persisted app.models.ObjectiveResult table (which has required game_id/team_id FKs) -- that table is populated later by task-26 using this functions output plus task-22s, not by this task.
4. Per-team normalization (AC #1, #2): present members for a team on the game date = that teams roster (team_memberships[team_id]) intersected with the consultant_ids that actually appear in objective_results (task-22 already omits PTO and no-assigned-work consultants from its output, so this intersection directly gives Section 7s present member set with no separate PTO input needed here). normalized_score = sum(present members points) / present_member_count. AC #2s fairness test: a 3-member team and a 5-member team where every member scores the same points must produce the same normalized_score despite different raw sums, directly demonstrating SPEC.md Section 7s stated purpose (normalization keeps 3-person teams competitive vs 5-person).
5. Team bonus (AC #3): +10 added to a teams normalized score only if present_member_count > 0 and every present members ObjectiveResult.projected_by_11 is true -- a partial team (some hit, some missed) never receives the bonus, verified by a dedicated test alongside the all-hit case.
6. Postponement and byes (AC #5): if either side of a Game has zero present members (team_memberships intersected with objective_results is empty for that team_id), the whole game is marked postponed=True, with both scores None and no winner/draw -- this reading treats team entirely on PTO -> game postponed/voided (SPEC.md Section 7) as applying to the whole game whenever either side is fully absent, not only when both are. A bye team (SPEC.md Section 7: odd team count -> one bye) simply has no Game row in the input games list for that date at all -- each game is resolved independently, so its absence cannot perturb any other games computed scores; a dedicated test constructs one game while a bye teams roster/results exist unused in the inputs, confirming the processed games scores are unaffected.
7. Winner/draw resolution (AC #4): resolves SPEC.md Section 11, item 1, which is explicitly still an open decision with only a stated preference (recommend draw flag), not a recorded resolution -- this plan adopts that stated recommendation as the resolution, since it is the only concrete direction given anywhere in the docs, flagged for hostile review to confirm/challenge same as task-22s working-slot interpretation. Higher final score (normalized + bonus) wins; equal non-postponed scores set is_draw=True and winner_team_id=None (no both-win path implemented).
8. Table-driven tests (test_team_scoring.py): normalization correctness, the 3-vs-5-member fairness case, bonus applied/not-applied, a home win / away win / draw, a fully-postponed game (one side absent), and byes-do-not-affect-other-games. Measure branch coverage with pytest-cov (already added as a dev dependency in task-22, will also need duplicating onto this branch per step 1s pattern) to confirm no regression below the coverage bar this codebase is now establishing for scoring modules, even though this AC set does not itself name a specific coverage percentage.
9. Verification pass: run pytest (with coverage) and ruff.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (2 warning(s), 2 minor(s))

- Warning: the either side absent -> whole game postponed reading of SPEC.md Section 7 (team entirely on PTO -> game postponed/voided) is a defensible, natural reading, but not the only conceivable one -- an alternative is that only both sides absent postpones the game, with a single absent side instead producing an automatic forfeit-win for the other team. Not blocking since the plans reading is directly supported by the sentences own wording (a team, singular, triggers game, the whole matchup), but should be confirmed/documented as an explicit interpretation during implementation, same as the draw-handling decision.
- Warning: the plan does not specify that team_memberships lookups must use a defensive default (e.g. .get(team_id, set())) rather than assuming every Games team_id is always present as a dict key -- a missing key would raise KeyError on malformed/incomplete input rather than degrading gracefully to zero present members -> postponed.
- Minor: the plan does not explicitly state GameResult.winner_team_id/is_draw values when postponed=True (implied None/False) -- should be made explicit in both code and tests to avoid ambiguity.
- Minor: the plan only names a one-side-absent postponement test; should also add a symmetric both-sides-absent case to fully exercise the branch.

IMPLEMENTATION SUMMARY

What was implemented:
- backend/app/team_scoring.py (new): resolve_games(objective_results, team_memberships, games) -> list[GameResult], a pure function with no I/O implementing SPEC.md Section 7. Continues the same pipeline stage the architecture notes describe (objective engine -> team scoring -> game winners), still before write results (the not-yet-built nightly reveal job, task-26). Defines GameResult (game_id, home/away_team_id, home/away_score, home/away_bonus_applied, winner_team_id, is_draw, postponed).
- backend/tests/test_team_scoring.py (new): 12 tests, 100% branch coverage, covering every AC directly plus the edge cases hostile plan review flagged (both-sides-absent postponement, a team missing entirely from team_memberships defaulting safely to zero present members).
- backend/app/objective_engine.py, backend/tests/test_objective_engine.py, backend/pyproject.toml (pytest-cov), .gitignore (.coverage): duplicated from task-22 onto this branch, since task-23 depends on task-22 which is Done but not yet merged into main -- the same accepted, already-documented pattern used across task-20/task-1/task-21/task-22 for this exact reason.

Key technical decisions:
- Present members = a teams roster (team_memberships) intersected with the consultant_ids appearing in objective_results. Since the objective engine already omits PTO and no-assigned-work consultants from its output, this intersection directly gives SPEC.md Section 7s present member set with no separate PTO input needed in this module.
- Postponement (AC #5-adjacent): resolves SPEC.md Section 7s team entirely on PTO -> game postponed/voided as applying to the whole game whenever either side has zero present members, not only when both do -- a defensible, direct reading flagged during hostile plan review, now documented as a resolved interpretation in the modules docstring. team_memberships.get(team_id, set()) is used defensively (per the hostile reviews warning) so a team missing entirely from the mapping degrades to zero present members -> postponed, rather than raising KeyError.
- Draw handling (AC #4): resolves SPEC.md Section 11, item 1, which is explicitly still an open decision with only a stated preference (recommend draw flag), not a recorded resolution -- this implementation adopts that stated preference, since it is the only concrete direction given anywhere in the docs. Equal non-postponed scores produce is_draw=True, winner_team_id=None; no both-win path implemented.
- Byes (AC #5): a bye team simply has no Game row in the games input for that date -- each game is resolved fully independently (no shared state across iterations of the loop in resolve_games), so a bye teams roster/results existing but unused cannot perturb any other games computed scores. Verified directly by a test that includes a bye teams roster and a stray result alongside one real game.
- Uses real app.models.Game instances directly as input (constructed in-memory with an explicit id for tests, no DB session needed), matching the established codebase precedent of pure functions accepting real SQLAlchemy model instances (timeentry.py, objective_engine.py) rather than inventing parallel dataclasses.
- Kept entirely separate from the already-existing, separately-persisted app.models.ObjectiveResult table (which has required game_id/team_id foreign keys) -- that table is populated later by task-26 using this functions and task-22s outputs together, not by this task.

Integration points:
- Imports ObjectiveResult from objective_engine.py (duplicated onto this branch, see above) and Game from app.models. No new production dependencies.
- Caught and fixed during implementation (test-authoring mistake, not a plan deviation): the tests _result() helper originally defaulted projected_by_11=True, silently applying the team bonus in tests not intended to exercise it (normalization, fairness, byes) and producing wrong expected values. Fixed by defaulting to False and only setting True explicitly in the bonus-specific tests.

Testing coverage:
- 78 backend pytest passed (38 pre-existing + 28 duplicated objective_engine tests + 12 new team_scoring tests), ruff clean.
- 100% branch coverage measured directly via pytest --cov=app.team_scoring --cov-branch.
- All 5 ACs verified against passing tests: normalization correctness, 3-vs-5-member fairness (equal per-member points produce equal normalized scores despite different raw sums), team bonus applied/not-applied, higher-score-wins plus a genuine draw (not both-win), and byes not affecting other games scores.
- E2E: skipped -- pure backend module, no I/O, no API endpoint, no UI surface.

Future considerations:
- Once task-26 (nightly reveal job) is built, it becomes the actual caller: constructing team_memberships from TeamMembership rows, games from scheduled Game rows, and using this functions GameResult output (together with task-22s ObjectiveResult output) to populate the persisted app.models.ObjectiveResult rows (with their required game_id/team_id) and Game.home_score/away_score/state -- this task does not implement that caller or any persistence.
- The either-side-absent-postpones-the-whole-game and draw-flag interpretations documented above should be revisited if/when SPEC.md Section 11s open decisions are formally resolved.
- Task-25 (game scheduling, not yet built) is what will actually produce the games list and decide which team gets a bye each date -- this task assumes that schedule is already given.

CODE REVIEW: Approved with 2 minor suggestions.

No critical or major issues found. Code is clean, well-organized, DRY (shared _present_results/_team_score helpers avoid duplicating home/away logic), and directly matches the design decisions documented in the plan, hostile review, and Implementation Notes -- including the defensive team_memberships.get(team_id, set()) the hostile review specifically asked for.

Minor, non-blocking:
- The draw determination (home_score == away_score) relies on exact float equality. Given the bounded, small-integer inputs here (points 0-30, team sizes 3-5, a flat +10 bonus), this is safe in practice and the test suite confirms it (3-vs-5 fairness test produces exactly equal floats). Worth revisiting with a tolerance-based comparison (math.isclose) only if this module later takes less-bounded or externally-sourced inputs.
- winner_team_id: int | None = game.home_team_id declares its type annotation mid-block (inside the if branch) rather than before the if/elif/else chain -- functionally fine and ruff-clean, but a style nit; declaring winner_team_id: int | None = None upfront and reassigning in each branch would read slightly more conventionally.

Requirements alignment: all 5 ACs verified against passing tests (100% branch coverage on the new module). No scope creep -- persistence, dividends, and market mechanics remain correctly out of scope, matching the architecture notes ordering. No security issues (pure function, no I/O, no external input parsing). No unnecessary dependencies (pytest-cov already justified for task-22, reused here).
<!-- SECTION:NOTES:END -->
