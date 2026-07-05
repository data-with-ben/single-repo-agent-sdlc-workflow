---
id: TASK-24
title: T3.1 Season and team assignment
status: Done
assignee:
  - '@agent'
created_date: '2026-07-03 15:26'
updated_date: '2026-07-05 03:13'
labels:
  - backend
dependencies:
  - TASK-23
references:
  - feature/task-24-season-team-assignment
modified_files:
  - backend/app/season.py
  - backend/tests/test_season.py
  - backend/pyproject.toml
  - .gitignore
  - backlog/backlog/tasks/task-24 - T3.1-Season-and-team-assignment.md
priority: medium
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create seasons and randomly partition active consultants into teams of 3-5 members, reshuffling teams when a new season starts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Teams are within the 3-5 member size bounds
- [x] #2 Team assignment is random but every active consultant is placed on a team
- [x] #3 Reshuffling at a new season produces different teams
- [x] #4 Season lifecycle (upcoming, active, complete) is enforced
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. New module backend/app/season.py with DB-backed service functions (real I/O, unlike task-22/23s pure functions -- nothing in this tasks ACs describes an HTTP request/response shape or status codes, unlike task-18s explicitly API-shaped ACs, so this is implemented as callable service functions, not a new route, resolved during assess-task and flagged here for hostile review to confirm):
   - create_season(db, name, start_date, end_date, team_size) -> Season: validates 3 <= team_size <= 5, creates a Season row with status=upcoming.
   - assign_teams(db, season, rng=None) -> list[Team]: the core partition (AC #1, #2). rng defaults to a fresh random.Random() (true randomness in production) but accepts an explicit seeded Random for deterministic tests -- needed to reliably demonstrate AC #3 (different reshuffles produce different teams) without a flaky test relying on incidental randomness.
   - start_new_season(db, name, start_date, end_date, team_size) -> Season: enforces the lifecycle (AC #4) -- transitions any currently active season to complete, creates the new season, calls assign_teams, then sets the new seasons status to active. Ensures only one season is ever active at a time.
2. Active consultants (AC #2) = User rows where status == active and consultant is in roles -- matches the PTO/status-exclusion pattern already established in objective_engine.py/team_scoring.py. Admins who are also consultants (roles include both) are included, per SPEC.md Section 2 (a user may hold both roles on one account).
3. Team-size partitioning algorithm (AC #1): given N active consultants and a target team_size, compute min_teams = ceil(N/5) and max_teams = floor(N/3) -- the range of team counts for which an all-teams-between-3-and-5 partition is mathematically possible. If min_teams > max_teams (fewer than 3 active consultants total, or another N for which no valid partition exists), raise ValueError rather than silently producing an out-of-bounds team -- not addressed by the ACs but a real edge case worth an explicit, documented decision rather than a silent bug. Otherwise choose num_teams as the value in [min_teams, max_teams] closest to round(N / team_size), then distribute members as evenly as possible (base = N // num_teams members per team, with the first N % num_teams teams getting one extra) -- this guarantees every team lands within the 3-5 bounds for any valid N, not just the common case.
4. assign_teams shuffles the active consultant list using the given (or fresh) Random instance before partitioning, satisfying AC #2s random requirement -- every active consultant appears in exactly one of the computed groups, so placement is total by construction, not by a separate check.
5. Re-assignment safety: if the given season already has Team rows (e.g., assign_teams is called again to manually reshuffle before the season starts), existing Team and TeamMembership rows for that season are deleted first, so re-running produces a clean replacement rather than duplicate/orphaned teams.
6. AC #3 (reshuffling produces different teams) is demonstrated with two explicit, different seeded Random instances passed to two separate assign_teams calls against the same consultant pool, asserting the resulting team compositions differ -- deterministic and reproducible, not reliant on incidental randomness that could flake.
7. Mid-season joins/new hires are explicitly out of scope -- SPEC.md and the backlog already carry a separate, later task (task-32, New-hire IPO at season boundaries) for that concern; this task only assigns the active roster at the moment a season starts.
8. Table-driven tests (test_season.py) using an in-memory/temp SQLite fixture matching the existing db_and_client pattern (test_main_timeentry.py): team sizes stay within 3-5 across several N values including edge cases (exactly 3, exactly 5, a remainder that would otherwise produce an out-of-bounds team without the range-based algorithm), every active consultant placed exactly once, a PTO/inactive consultant excluded, the too-few-consultants error case, reshuffling with two seeds producing different team compositions, and season lifecycle enforcement (starting a new season completes the previously active one, only one season active at a time).
9. Verification pass: run pytest (with coverage, matching the bar task-22/23 established for scoring modules) and ruff.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (2 warning(s), 1 minor)

- Warning: the range-based team-size partitioning algorithm (min_teams=ceil(N/5), max_teams=floor(N/3)) is a standard, mathematically sound balanced-partition technique -- traced through several worked examples (N=8, 13, 20) confirming it holds -- but this class of ceiling/floor arithmetic is a classic source of off-by-one bugs. The plan only names a handful of specific edge-case tests. Strengthen with a broader test sweep (e.g. every N from 3 to 50) asserting all resulting team sizes stay within 3-5, not just the named cases.
- Warning: Team.name is a NOT NULL column, but the plan never specifies how team names are generated during assign_teams. Must be resolved during implementation (e.g. Team 1, Team 2... scoped per season), not left as an afterthought.
- Minor: create_season/start_new_season fuses creation and immediate activation, so upcoming may be a transient, barely-observable state rather than something an admin can pre-schedule ahead of time. Not blocking since AC #4 does not require standalone scheduling, but worth flagging for a future task/UI that might want to schedule a season in advance.

IMPLEMENTATION SUMMARY

What was implemented:
- backend/app/season.py (new): create_season, assign_teams, and start_new_season -- DB-backed service functions (real I/O, unlike task-22/23s pure functions) implementing SPEC.md Section 7s season/team lifecycle. No new HTTP endpoint: nothing in this tasks ACs describes a request/response shape, so this is a callable service layer, resolved during assess-task and confirmed during hostile plan review.
- backend/tests/test_season.py (new): 59 tests, 100% branch coverage, including a 48-value N sweep (3 through 50) verifying every resulting team stays within 3-5 members across the whole practical range, not just a few named edge cases -- directly addressing the hostile plan reviews warning about off-by-one risk in ceiling/floor arithmetic.
- backend/pyproject.toml (pytest-cov), .gitignore (.coverage): same pattern already established in task-22/23 for measuring branch coverage.

Key technical decisions:
- Team-size partitioning (AC #1): min_teams = ceil(N/5), max_teams = floor(N/3) define the range of team counts for which an all-teams-between-3-and-5 partition is mathematically possible; num_teams is chosen as the value in that range closest to round(N/team_size), then members are distributed as evenly as possible (base = N // num_teams, first N % num_teams teams get one extra). This is a standard balanced-partition technique that guarantees the bounds for any N >= 3, verified by the 48-value sweep rather than assumed correct from a few worked examples.
- Fewer than 3 active consultants (N < 3, or any N for which min_teams > max_teams) raises ValueError rather than silently producing an out-of-bounds team -- not explicitly addressed by the ACs, but a real edge case that would otherwise violate AC #1 silently.
- Active consultants (AC #2) = User rows with status == active and consultant in roles, matching the PTO/status-exclusion pattern already established in objective_engine.py/team_scoring.py. A user with only the admin role (no consultant role) is excluded even if active, per SPEC.md Section 2s roles-are-flags-on-one-account model.
- assign_teams accepts an optional rng: random.Random parameter, defaulting to a fresh Random() in production (true randomness) but accepting an explicit seed for tests -- needed to deterministically demonstrate AC #3 (two different seeds produce different team compositions) without relying on incidental randomness that could flake.
- Team.name (a NOT NULL column the plan initially did not address, per hostile plan review) is auto-generated as Team 1, Team 2, ... scoped per assign_teams call.
- Re-calling assign_teams for a season that already has teams deletes the existing Team/TeamMembership rows first, so manually reshuffling before a season starts replaces rather than duplicates -- verified by a dedicated test.
- Season lifecycle (AC #4): start_new_season transitions any currently active season(s) to complete before creating and activating the new one, enforcing that at most one season is ever active. create_season and activation are fused into one atomic step (create_season alone leaves a season in upcoming, but nothing currently calls it standalone) -- flagged during hostile review as a minor gap if a future task wants to pre-schedule a season in advance without immediately activating it.

Integration points:
- No new production dependencies. Imports Season, Team, TeamMembership, User directly from app.models (no new models).
- Fixed during implementation (test-authoring mistake, not a plan deviation): the tests _make_consultants() helper originally generated emails from a per-call index (consultant0@example.com), causing a UNIQUE constraint collision when a test called it twice (e.g. 4 active + 1 pto). Fixed with a module-level counter shared across all calls.

Testing coverage:
- 97 backend pytest passed (38 pre-existing + 59 new), ruff clean.
- 100% branch coverage measured directly via pytest --cov=app.season --cov-branch.
- All 4 ACs verified: team sizes within 3-5 across N=3..50, every active consultant placed exactly once (PTO and non-consultant roles correctly excluded), two differently-seeded reshuffles producing different team compositions, and season lifecycle enforcement (new season completes the prior active one, only one active at a time).
- E2E: skipped -- backend-only service function, no API endpoint or UI surface.

Future considerations:
- Task-25 (game scheduling, not yet built) and task-26 (nightly reveal job, not yet built) are the eventual callers of this seasons teams for pairing/scoring -- this task only creates the season and teams, nothing downstream.
- Mid-season joins/new hires are explicitly out of scope -- task-32 (New-hire IPO at season boundaries) owns that concern.
- If a future task needs to pre-schedule a season (create it as upcoming without immediately activating/assigning teams), create_season and assign_teams can already be called independently of start_new_season -- only the fused convenience path was exercised by this tasks tests.

CODE REVIEW: Approved with 1 minor suggestion (fixed).

No critical or major issues found. Code is clean, well-organized, and directly matches the design decisions from the plan and hostile review -- including the range-based partitioning algorithm, the defensive too-few-consultants error, auto-generated Team.name values, and the delete-before-recreate reassignment safety.

Fixed during review: start_date/end_date parameters on create_season and start_new_season had no type hints, inconsistent with this codebases established full type-hint discipline (objective_engine.py, team_scoring.py). Added datetime annotations. Re-ran full suite after the fix: 97 passed, ruff clean.

Requirements alignment: all 4 ACs verified against a 48-value N sweep plus targeted tests for randomness, PTO/role exclusion, and lifecycle enforcement. No scope creep -- game scheduling and reveal-job persistence remain correctly out of scope, matching the architecture notes ordering. No security issues (parameterized ORM queries throughout, no external input parsing). New dependency (pytest-cov) already justified in task-22/23, reused here for the same coverage measurement.
<!-- SECTION:NOTES:END -->
