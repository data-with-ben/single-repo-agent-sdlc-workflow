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

5. Bootstrap gitignored build artifacts so subsequent steps have working toolchains. Run all three installs from the worktree root:

```bash
# Node dependencies — frontend
cd "$WORKTREE_PATH/frontend" && npm ci

# Node dependencies — e2e
cd "$WORKTREE_PATH/e2e" && npm ci

# Python virtualenv + dependencies — backend
cd "$WORKTREE_PATH/backend"
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]" --quiet
```

If any install fails, emit `WORKTREE_BLOCKED: bootstrap failed — <error summary>` and stop. Do not continue with a broken toolchain.

6. Emit completion:
   - Emit `WORKTREE_READY: <absolute-path>` and continue to the next step in the workflow — do not stop.

## What the worktree contains

The worktree is a complete checkout of the feature branch at the moment of creation. Every directory and file in the repo is present: `frontend/`, `backend/`, `e2e/`, `backlog/`, `.claude/`, scripts — everything. All subsequent workflow steps operate from this worktree root as if it were the main workspace.

## Rules

- The `.claude/worktrees/` directory is already in `.gitignore` — no additional configuration needed
- Create a worktree only once per branch; if one already exists at the expected path, skip steps 2–4 and go straight to step 5 (bootstrap is idempotent — re-running `npm ci` / `pip install` on an existing install is safe and fast)
- Never create the worktree for a branch that is already checked out in the main repo (git will refuse this — they must be on different branches)
