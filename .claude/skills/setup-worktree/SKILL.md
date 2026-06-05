---
name: setup-worktree
description: Create a git worktree for the feature branch so all task work is isolated from the main checkout
---

You are the worktree setup agent. Your job is to create a dedicated git worktree for the current feature branch so all implementation, testing, and commit work runs in a branch-isolated environment without touching the main checkout.

## Process

1. Derive the worktree path. Worktrees live at `.claude/worktrees/<branch>` inside the repo root (already listed in `.gitignore`):

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
WORKTREE_PATH="$REPO_ROOT/.claude/worktrees/<branch>"
```

2. Create the parent directory if it doesn't exist:

```bash
mkdir -p "$REPO_ROOT/.claude/worktrees"
```

3. Create the worktree for the feature branch:

```bash
git worktree add "$WORKTREE_PATH" <branch>
```

4. Verify the worktree was created successfully:

```bash
git worktree list
```

5. Emit completion:
   - Emit `WORKTREE_READY: <absolute-path>` and continue to the next step in the workflow — do not stop.

## What the worktree contains

The worktree is a complete checkout of the feature branch at the moment of creation. Every directory and file in the repo is present: `frontend/`, `backend/`, `e2e/`, `backlog/`, `.claude/`, scripts — everything. All subsequent workflow steps operate from this worktree root as if it were the main workspace.

## Rules

- The `.claude/worktrees/` directory is already in `.gitignore` — no additional configuration needed
- Create a worktree only once per branch; if one already exists at the expected path, emit `WORKTREE_READY: <path>` and continue
- Never create the worktree for a branch that is already checked out in the main repo (git will refuse this — they must be on different branches)
