---
id: TASK-17
title: T0.3 Seed script
status: AI Code Review
assignee:
  - '@agent'
created_date: '2026-07-03 15:25'
updated_date: '2026-07-04 02:09'
labels:
  - foundation data
dependencies:
  - TASK-16
references:
  - feature/task-17-seed-script
modified_files:
  - backend/README.md
  - backend/app/seed.py
  - backend/tests/test_seed.py
  - backlog/backlog/tasks/task-17 - T0.3-Seed-script.md
priority: high
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Seed clients, roughly 15 consultants with varied punctuality profiles (e.g. always by 11am, chronic late, streaky), one active season with random teams, and empty portfolios/wallets with a starting balance. This is what makes every later screen and the nightly job exercisable during development.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Running the seed script against an empty database produces data sufficient to exercise every screen and the nightly job
- [x] #2 Seeded consultants have varied, clearly distinguishable punctuality profiles
- [x] #3 Re-running the seed script is idempotent or clearly resets prior seed data
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add backend/app/seed.py as a runnable module (python -m app.seed) that seeds against the engine from app/db.py. Assumes migrations have already been applied (documented in README); does not run Alembic itself.
2. Idempotency strategy: seed() first deletes all rows from every seed-managed table in FK-safe order (children before parents), then inserts fresh data. This makes "idempotent or clearly resets" (AC #3) unambiguous -- re-running always produces the same row counts, never duplicates.
3. Seed data: 3 Clients (active); ~15 consultant Users plus 1-2 admin/manager Users (roles per SPEC.md Section 2); Assignments linking each consultant to 1-2 clients; one active Season with team_size=4; teams randomly partitioned from the 15 consultants (3-5 members each) via TeamMembership rows; a Wallet per user with a starting balance (e.g. 100.0) and no Holdings ("empty portfolios" per the task description -- Wallets exist, Holdings do not).
4. Punctuality profiles (AC #2): assign each seeded consultant one of three profile labels used only to generate realistic TimeEntry timestamp patterns during seeding (not a stored DB field, since User has no such column) -- "always-on-time" (projectedAt/loggedAt consistently well before the 11am/EOD reference points), "chronic-late" (consistently after them, or missing loggedAt entirely on some days), "streaky" (alternating). Seed the last 5 workdays of TimeEntry rows per consultant reflecting their profile, using UTC timestamps directly against fixed reference hours (11:00/15:00/18:00 UTC) -- deferring proper per-user timezone modeling to task-22's objective engine work, since User currently has no timezone field and this task only needs visibly varied data, not scoring correctness.
5. Do not pre-seed Game, ObjectiveResult, Dividend, or Transaction rows -- those are outputs the nightly job (task-26) computes from TimeEntry + Team + Season, not seed inputs. Note this explicitly as a scope boundary so it isn't mistaken for a missed AC.
6. Tests (backend/tests/test_seed.py): running seed() against a fresh migrated temp DB produces the expected counts (3 clients, ~15+ users, 1 active season, teams covering all consultants, one wallet per user with the starting balance); at least one consultant's entries are all before the 11am reference and at least one consultant's are not, demonstrating AC #2's variation; running seed() twice leaves row counts unchanged (verifies AC #3).
7. Update backend/README.md with the seed command and the required order (alembic upgrade head, then python -m app.seed).
8. Verification pass: run the new tests, run ruff, and manually run the seed script against a throwaway local DB to eyeball the output before handing off to unit-tests.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
HOSTILE PLAN REVIEW - PASSED (3 warning(s))

- Warning: AC #1 says 'against an empty database' -- clarify explicitly (seed.py docstring and README) that this means a freshly migrated database with no rows, not a database with no schema; the seed script does not run migrations itself.

- Warning: consider seeding at least one dual-role user (admin+consultant), matching SPEC.md Section 2's stated design that a manager 'may also be consultant and holder'. Not blocking, but gives future admin-dashboard work a realistic account to test against.

- Warning: strengthen the AC #2 test beyond a binary 'at least one before / at least one not before' check -- assert all three punctuality profile categories (always-on-time, chronic-late, streaky) are actually represented among the seeded consultants, so 'varied, clearly distinguishable' is verified across the full set, not just two data points.

E2E: skipped -- this is a backend-only dev/test data seed script with no UI or user-facing workflow; none of the three ACs require e2e coverage.

IMPLEMENTATION NOTES

What was implemented:

- backend/app/seed.py: a runnable seed module (python -m app.seed) that resets all seed-managed tables (children before parents, FK-safe) then inserts 3 clients, 16 users (15 consultants including one dual-role admin+consultant, plus a dedicated manager), ~21 client assignments, one active Season (team_size=4), 4 teams (sized 4/4/4/3) covering all 15 consultants via TeamMembership, a Wallet per user with a 100.0 starting balance and no Holdings, and 5 workdays of TimeEntry rows per consultant shaped by one of three punctuality profiles (always-on-time, chronic-late, streaky).

- Fixed random.seed(42) inside seed() so every run is byte-identical -- not just row-count-stable -- which is a stronger and simpler idempotency guarantee than relying on random choices happening to net out to the same totals.

- backend/tests/test_seed.py: three tests covering expected data shape/counts, representation of all three punctuality profiles (not just a binary before/after check, per hostile-review feedback), and idempotency across two consecutive seed() calls.

- Updated backend/README.md with the seed command and required order (migrate, then seed).

Key technical decisions (resolving hostile-plan-review warnings):

- Documented explicitly (in seed.py's module docstring and the README) that "empty database" means freshly migrated with no rows, not missing schema -- the seed script never touches migrations.

- Added a dual-role user (roles=["admin","consultant"]) matching SPEC.md Section 2's "may also be consultant and holder" design, so future admin-dashboard work has a realistic account to test against.

- Punctuality profiles are seed-time-only labels (not a stored DB column, since User has no such field) used purely to shape TimeEntry timestamp patterns; thresholds are evaluated directly in UTC against fixed reference hours (11:00/15:00), deferring true per-user timezone modeling to task-22's objective engine.

- Deliberately did not pre-seed Game/ObjectiveResult/Dividend/Transaction rows -- those are the nightly job's (task-26) outputs, not seed inputs.

Integration points:

- No new dependencies. New files: app/seed.py, tests/test_seed.py.

- backend/README.md updated with the seed workflow.

Testing coverage:

- pytest: 8 of 8 passed (5 pre-existing, 3 new seed tests).

- ruff: clean.

- Manually ran the seed script twice against a throwaway local DB and confirmed identical row counts (3/16/21/1/4/15/16/75) before writing the automated idempotency test.

Future considerations:

- task-22 (objective engine) will need a real per-user timezone source before "local zone" threshold evaluation is accurate; this seed script's UTC-only approach is a known, documented gap until then.

- task-18+ (client/consultant screens) and task-26 (nightly job) are the first real consumers of this seed data.

CODE REVIEW: Approved with 1 minor (fixed inline: removed unused EOD_UPDATE_HOUR constant)

SELF-IMPROVEMENT: task-16 broke 'pip install -e .[dev]' from a clean environment (setuptools package discovery ambiguity from adding alembic/), but this wasn't caught until task-17's fresh worktree bootstrap failed on it. The CI workflow set up in task-15 runs exactly this install command on a clean GitHub Actions runner on every push -- it would have caught this the moment task-16 was pushed, but nobody checked whether CI actually passed after the push, only that local tests passed (against a venv that already had the package installed from before the regression). Recommend: after pushing a task's branch (or after merging to main) during closeout, check the CI run status via 'gh run list --branch <branch> --limit 1' or 'gh run watch', and treat a CI failure as equivalent to a local test failure -- don't rely solely on local venvs, which can mask fresh-install regressions that only a truly clean environment surfaces.
<!-- SECTION:NOTES:END -->
