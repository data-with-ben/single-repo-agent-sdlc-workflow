---
id: TASK-26
title: T3.3 Nightly reveal job (idempotent)
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:27'
updated_date: '2026-07-05 13:53'
labels:
  - backend
dependencies:
  - TASK-25
references:
  - feature/task-26-nightly-reveal-job
modified_files:
  - .gitignore
  - backend/pyproject.toml
  - backend/app/dividends.py
  - backend/app/game_scheduling.py
  - backend/app/objective_engine.py
  - backend/app/pricing.py
  - backend/app/reveal.py
  - backend/app/season.py
  - backend/app/team_scoring.py
  - backend/app/trading.py
  - backend/tests/test_dividends.py
  - backend/tests/test_game_scheduling.py
  - backend/tests/test_objective_engine.py
  - backend/tests/test_pricing.py
  - backend/tests/test_reveal.py
  - backend/tests/test_season.py
  - backend/tests/test_team_scoring.py
  - backend/tests/test_trading.py
  - backlog/backlog/tasks/task-26 - T3.3-Nightly-reveal-job-idempotent.md
priority: medium
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Orchestrates the objective engine, team scoring, and game resolution: writes ObjectiveResults and Game scores, credits Dividends and Wallets, and recomputes prices. Runs at reveal time and must be safe to re-run for the same date.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Running the job twice for the same gameDate produces identical results (idempotent, keyed on date)
- [x] #2 Wallets and dividends are not double-credited on re-run
- [x] #3 A failure mid-run leaves the system in a recoverable state
- [x] #4 Unit and integration tests run the job over seed data end to end
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Plan for task-26 (T3.3 Nightly reveal job, idempotent):

All of this task's real prerequisites now exist and are ported onto this
branch from their (still unmerged) source branches: objective_engine
(task-22), team_scoring (task-23), game_scheduling (task-25, for the
already-scheduled Game rows this job reads), pricing/trading (task-28/29),
and dividends (task-30). This task's own job was previously blocked because
those did not exist yet; now it becomes the thin orchestrating caller its
own description describes.

New module: backend/app/reveal.py -- a single DB-writing entry point,
reveal_game_date(db, game_date), that runs the pipeline named in SPEC.md
Section 10: objective engine -> team scoring -> game winners -> write
results/dividends/wallets -> recompute prices.

1. Gather inputs for game_date: TimeEntry rows for that work_date, the set
   of PTO consultant user_ids, and every Game scheduled for that date
   (already written by task-25's game_scheduling.schedule_season_games).
   Build team_memberships for every team appearing in those games (query
   TeamMembership for those team_ids) and a reverse consultant_id ->
   team_id map from it.

2. Run objective_engine.compute_objective_results(entries, game_date,
   pto_ids) to get the pure ObjectiveResult list (no I/O yet).

3. Persist ObjectiveResult DB rows (writes ObjectiveResults). Real design
   gap this step must resolve: app.models.ObjectiveResult has a non-
   nullable game_id FK (a normalization added on top of SPEC.md's literal
   data model, per that model's own docstring), but a consultant whose
   team has a bye that date has no Game row to attach to. Resolved by only
   persisting a DB row for consultants whose team appears in an actual
   Game that date (found via the reverse team map built in step 1) --
   their computed objective points still feed team scoring in-memory for
   that game, but a bye-team consultant's objective points for that date
   are not written to the ObjectiveResult table, since there is no valid
   game_id to store. Flagged for hostile review as a resolved
   interpretation, not a silently-dropped requirement.
   Idempotency (AC #1/#2): delete any existing ObjectiveResult rows for
   this exact game_date before inserting the freshly computed ones, the
   same delete-and-recreate pattern already used by
   season.assign_teams/game_scheduling.schedule_season_games -- since the
   computation is deterministic given the same TimeEntry data, re-running
   produces byte-identical rows.

4. Run team_scoring.resolve_games(objective_results, team_memberships,
   games) to get GameResult objects, then write each game's home_score/
   away_score/state (final)/revealed (True) back onto its existing Game
   row. This is naturally idempotent: overwriting the same computed fields
   with the same deterministic values on a re-run changes nothing.

5. Run dividends.compute_dividend_awards(objective_results,
   team_memberships, game_results) and dividends.credit_dividends(db,
   game_date, awards) to credit Dividends and Wallets. This step is
   already idempotent by construction (task-30's per-(user, consultant,
   game_date, reason) guard-check) -- no new idempotency logic needed
   here, just wiring the call.

6. Recompute prices: trading.py (task-29) already computes rolling_avg_
   score and demand_pressure live from ObjectiveResult/Transaction history
   at the moment of any trade, rather than storing a price the reveal job
   would need to refresh -- there is no persisted price value anywhere in
   SPEC.md's required data model for this step to update. This step is
   therefore a documented no-op under the existing architecture: once
   ObjectiveResult rows are written in step 3, any subsequent price quote
   automatically reflects the new data with no separate recompute call
   needed. Flagged for hostile review as a resolved interpretation, since
   the task description explicitly names recomputes prices as a
   pipeline step.

7. AC #3 (a failure mid-run leaves a recoverable state): every ported
   module here only ever flushes (never commits) internally, matching the
   established convention. reveal_game_date wraps its entire body in a
   try/except that calls db.rollback() and re-raises on any exception,
   rather than relying on the caller to remember to roll back -- this
   guarantees no partial writes are ever left in a committed state
   regardless of caller discipline.

8. Tests (backend/tests/test_reveal.py):
   - AC #1: running reveal_game_date twice for the same game_date produces
     byte-identical ObjectiveResult rows, Game scores, and Dividend rows
     (same row counts and same field values, not just no crash).
   - AC #2: wallet balances after the second run equal wallet balances
     after the first run (no accumulation).
   - AC #3: a test that forces an exception partway through (e.g. by
     monkeypatching one of the pipeline steps to raise) asserts the
     session rolls back to its pre-call state -- no ObjectiveResult, Game
     score, or Dividend row is left behind from the failed attempt.
   - AC #4: an integration test that calls app.seed.seed(), schedules
     games for one of the seeded workdays via
     game_scheduling.schedule_season_games, runs reveal_game_date for
     that date, and asserts it completes without error and produces a
     sane result set (at least one ObjectiveResult row, at least one
     finalized Game, and wallet balances reflecting any dividends earned)
     -- this is the ports-end-to-end-over-real-seed-data proof the AC
     asks for, not a synthetic minimal fixture.
   - Bye-team handling: a consultant on a bye team that date produces no
     ObjectiveResult DB row (proving the resolved interpretation from step
     3 is actually implemented, not just described).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
BACKLOG GAP: This task's Dependencies field only lists TASK-25, but its own description requires crediting Dividends and Wallets and recomputing prices -- functionality owned by TASK-28 (pricing), TASK-29 (buy/sell/wallet), and TASK-30 (dividend payout), none of which exist yet in any branch. Not implementable until those land. Recommend adding them as declared dependencies. Skipped for now in favor of TASK-28, which has no such blocker.

HOSTILE PLAN REVIEW - PASSED (1 warning, 1 minor): (1) game_date must be normalized to a datetime at midnight before querying Game.game_date/TimeEntry.work_date for equality, mirroring dividends.py's game_date_midnight pattern -- a plain date object could silently fail to match rows; (2) AC1's identical-results-on-rerun assumes unchanged underlying data between runs -- new TimeEntry rows logged between calls legitimately change the second run's output, not an idempotency bug.

E2E TESTS: Skipped -- backend-only orchestration module (reveal.py), no HTTP endpoint or UI surface. AC4's end-to-end proof is covered by TestRevealOverSeedData, an integration test running the full pipeline against app.seed.seed()'s real data.

IMPLEMENTATION NOTES: Added backend/app/reveal.py (reveal_game_date), orchestrating objective_engine -> team_scoring -> game score writes -> dividends per SPEC.md Section 10. This task was originally blocked (see the BACKLOG GAP note above) since its description needs task-28/29/30's functionality that did not exist yet; all of it now does, ported from those branches (none yet merged) alongside objective_engine (task-22), team_scoring (task-23), game_scheduling (task-25), and season (task-24, needed by the test fixtures). Resolved two real design gaps: (1) app.models.ObjectiveResult has a non-nullable game_id FK, but a bye-team consultant has no Game to attach to -- resolved by only persisting a DB row for consultants whose team appears in an actual Game that date, verified by a dedicated bye-team test; (2) recompute prices has no persisted price value to update anywhere in SPEC's required data model, since trading.py already computes prices live from history -- documented as a no-op under the existing architecture. Idempotency: ObjectiveResult rows are deleted and recreated per game_date (matching season.py/game_scheduling.py's precedent); Game score writes are naturally idempotent; dividend crediting is already idempotent by construction (task-30). Recoverable failure (AC3): the whole body is wrapped in try/except that rolls back and re-raises on any exception, verified by a test that monkeypatches credit_dividends to raise and asserts zero partial writes remain. AC4's seed-data proof: an integration test that runs app.seed.seed() into an isolated in-memory-backed engine (patching app.seed's own SessionLocal reference, not app.db's, since seed.py binds the name at import time), builds a season/teams/schedule aligned to the seeded TimeEntry dates, and runs the full pipeline end to end. Tests: 6 new, 100% branch coverage. Full backend suite: 275 passed, ruff clean.

CODE REVIEW: Approved with 0 issues. Ruff clean, 275 tests pass, 100% branch coverage on app.reveal. Noted a postponed game is marked state=final (with null scores) since the Game model's state enum has no separate postponed value -- the only fit within the existing schema, not a new gap.

AUDIT: All workflow steps verified complete (intake, worktree, assess, plan, hostile review, implement, verify-ac, unit-tests, e2e-skip, notes, code-review, this audit).
<!-- SECTION:NOTES:END -->
