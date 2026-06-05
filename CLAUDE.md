# CLAUDE.md

## Repo Architecture

This is a mono-repo. All project areas are top-level subdirectories:

- **frontend/** — React 18+ with TypeScript, Vite, and Vitest
- **backend/** — FastAPI with Python 3.11+
- **e2e/** — Playwright end-to-end tests
- **backlog/** — Backlog.md CLI-based task management (managed with manage-backlog-tasks skill)

All commits and branches live in this single git repo. Never reference a separate "coordination repo" or `projects/` directory — those concepts do not apply.

## SDLC Workflow System

The `.claude/skills/` directory contains custom Claude Code skills that implement a full SDLC automation workflow:

**Primary Skill:**
- **workflow** - The main end-to-end coordinator. Use when the user asks to coordinate a task. Claims work from backlog, runs intake, plans, implements, tests, reviews, and closes out tasks autonomously.

**Component Skills** (called by workflow):
- **check-for-work** - Claims tasks from backlog by ID or priority
- **unit-tests** - Creates/updates and runs unit tests
- **e2e-tests** - Runs Playwright end-to-end tests
- **implementation-notes** - Documents implementation details in task
- **code-review** - Performs comprehensive code quality review
- **commit** - Creates conventional commit messages
- **audit-followed-workflow-steps** - Verifies all workflow steps completed
- **manage-backlog-tasks** - Wraps all backlog CLI operations

The workflow skill enforces a strict process (see `.claude/skills/workflow/SKILL.md`):
1. Check for work → 2. Run intake (create branch) → 3. Assess task definition → 3b. Optional human intake review → 4. Plan the task → 4b. Optional human plan review → 5. Implement changes → 6. Verify acceptance criteria → 7. Unit tests → 8. E2E tests → 9. Write implementation notes → 10. AI code review → 10b. Optional human code review → 11. Audit all steps → 11b. Self-improvement recommendation → 12. Merge guard (scope check) → 13. Closeout (squash, push, mark done)

**Key workflow behaviors:**
- Always use `backlog` CLI for task operations (never edit task files directly via manage-backlog-tasks)
- Run `backlog` commands from inside the `backlog/` directory
- Uses gitflow branch naming: `feature/<task-id>-description`, `fix/<task-id>-description`, etc.
- Commits after every major step using the `commit` skill
- Merge guard (Step 12) runs **before** marking the task Done — compares `<upstream>..HEAD` against the task's `modified_files` to detect scope creep
- Retries are bounded: AC verification, unit tests, e2e tests max 2 retries each; code review max 1 fix iteration
- Emits `TASK_COMPLETE: <id> — <title>` on success or `WORKFLOW_BLOCKED: <reason>` on failure

## Working with the Workflow

When the user says "coordinate a task" or wants full SDLC automation, invoke the `workflow` skill. It will handle the entire lifecycle autonomously. The workflow operates on one task at a time and requires a feature branch (blocks if on main/master/develop).

For manual operations, use individual skills like `unit-tests`, `e2e-tests`, `commit`, etc. or interact directly with the backlog CLI.
