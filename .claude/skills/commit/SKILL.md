---
name: commit
description: Commit all changes with a well-formatted commit message following conventional commits
---

Your job is to commit all pending changes with a clear, descriptive commit message.

This is a mono-repo. All changes across `frontend/`, `backend/`, `e2e/`, and `backlog/` are committed as a single git commit.

**Working root:** During an active workflow, commits are made from the worktree root (`<worktree>`), not the main repo checkout. The worktree is a complete checkout of the feature branch — running `git commit` there commits directly to the feature branch. If no worktree is active (e.g., a manual one-off commit outside the workflow), commit from the repo root as normal.

## Process

1. Check the current status from the workspace root:

```bash
git status
git diff --stat
```

2. **Skip if there is nothing to commit** — emit `COMMIT_NOOP: no changes to commit` and continue.

3. Review the task details to understand what was implemented:

```bash
cd backlog && backlog task <id> --plain
```

4. Stage only the changes belonging to this task. Prefer explicit paths over `git add .`:

```bash
git add <files modified by this task>
```

If the change set is clearly scoped to the task, `git add -A` is acceptable, but never include `.env`, credentials, or build artifacts that should be gitignored.

5. Create a commit message following conventional commits format. The `<scope>` should reflect the primary area changed (`frontend`, `backend`, `e2e`, `backlog`, or a compound like `frontend,backend` for cross-cutting changes):

```
<type>(<scope>): <subject>

<body>

Resolves: #<task-id>
```

**Type:** feat, fix, docs, style, refactor, test, chore
**Subject:** Short summary (50 chars or less)
**Body:** Detailed explanation of what and why (wrap at 72 chars)

6. Commit from the workspace root:

```bash
git commit -m "<commit message>"
```

7. Verify:

```bash
git log -1 --stat
```

8. Emit completion:
   - Emit `COMMIT_COMPLETE: <commit hash>` and continue on to the next step in the workflow - do not stop.
   - If no changes to commit: emit `COMMIT_NOOP: no changes to commit` and continue on to the next step in the workflow - do not stop.

## Commit Message Guidelines

**Subject line:**
- Use imperative mood ("add" not "added" or "adds")
- Don't capitalize the first letter
- No period at the end
- Be concise but descriptive

**Body:**
- Explain what and why, not how
- Wrap at 72 characters
- Separate subject from body with blank line
- Include context that would help reviewers understand the change

**Examples:**

```
feat(backend): add JWT-based authentication

Implements JWT authentication to replace session-based auth.
Provides better scalability for the API and enables stateless
authentication for mobile clients.

Resolves: #123
```

```
feat(frontend,backend): add user profile editing

Adds profile edit form in React with a matching FastAPI endpoint.
Validates fields server-side and returns structured errors.

Resolves: #456
```

## Rules

- Always commit from the workspace root — never cd into a subdirectory to commit
- All changes must be staged before committing
- Commit message must follow conventional commits format
- Include the task ID in the commit message footer
- Do not commit files that should be ignored (.env, node_modules, build artifacts, etc.)
