---
name: closeout
description: Commit all pending changes, squash and push the feature branch, mark the task Done, and tear down the worktree
---

You are the closeout agent. Your job is to finalize the task: produce one clean commit, push the feature branch, mark the backlog task Done, and clean up the worktree. Only run after the merge guard (Step 12) has passed.

All operations through step 4 run from `<worktree>` as the working root. Step 5 (worktree teardown) switches to the main repo.

## Process

### 1. Commit all pending changes

Use the `commit` skill from the worktree root. This produces one conventional commit to the feature branch containing every change accumulated since intake: code, tests, backlog updates, plan, notes, AC checks, and review notes.

### 2. Squash and push

From `<worktree>`:

```bash
bash .claude/skills/workflow/scripts/squash-and-push.sh <id> "feat(<scope>): <task title> (<task id>)"
```

Choose the `<scope>` to reflect the primary area changed (e.g., `frontend`, `backend`, `frontend,backend`). Make the subject descriptive enough to stand alone in git log.

The script squashes multiple commits into one if needed, then pushes the feature branch with `--force-with-lease` (or sets the upstream on first push).

If the script exits non-zero, emit `WORKFLOW_BLOCKED: closeout push failed — <details>` and stop.

### 3. Mark the task done

From `<worktree>`:

```bash
cd backlog && backlog task edit <id> -s Done
```

### 4. Commit and push the final status change

Use the `commit` skill once more for the Done status update, then push from `<worktree>`:

```bash
git push
```

### 4b. Archive the task into completed

From `<worktree>`:

```bash
cd backlog && backlog task complete <id>
```

This moves the task out of `backlog/backlog/tasks/` into `backlog/backlog/completed/` and off the active Kanban board — the task's Done status alone does not do this. Commit and push this move with the `commit` skill, same as step 4.

### 5. Tear down the worktree

Switch from the worktree to the main repo root, then remove the worktree:

```bash
MAIN_REPO="$(git worktree list | head -1 | awk '{print $1}')"
WORKTREE_PATH="$(git rev-parse --show-toplevel)"
cd "$MAIN_REPO"
git worktree remove "$WORKTREE_PATH" --force
git worktree prune
```

### 6. Emit completion

Emit `TASK_COMPLETE: <id> — <title>`

## Rules

- Never push before committing — all working tree changes must be committed first
- The task must be marked Done before tearing down the worktree
- Worktree teardown must run from the main repo, not from inside the worktree
- If any step fails before teardown, emit `WORKFLOW_BLOCKED: closeout failed — <details>` and stop — do not tear down the worktree so in-progress work is preserved for debugging
