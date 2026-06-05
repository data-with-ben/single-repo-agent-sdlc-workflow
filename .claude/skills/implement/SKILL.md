---
name: implement
description: Implement the planned changes for the current backlog task to production-grade standards
---

You are the implementation agent. Your job is to write production-grade code that satisfies the task's acceptance criteria according to the implementation plan.

## Process

1. Update the task status:

```bash
cd backlog && backlog task edit <id> -s "Code" -a @agent
```

2. Read the task to review the plan and acceptance criteria:

```bash
cd backlog && backlog task <id> --plain
```

3. Implement the changes step by step, following the plan:

   - **Match conventions** — use the same naming, error handling, and code style as the surrounding code. Read the files you're modifying before changing them.
   - **Dependencies** — when integrating a third-party library, always check the latest docs using context7 and check the actual package for implementation patterns. Do not guess the API.
   - **Minimal scope** — implement only what the acceptance criteria require. Nothing more.
   - **Documentation** — update README.md or other relevant docs for any integration or architectural change.

4. If implementation reveals that the plan is incorrect or incomplete, note the deviation before continuing:

```bash
cd backlog && backlog task edit <id> --append-notes "Plan deviation: <what changed and why>"
```

5. Do not commit — leave all changes in the working tree for the closeout step.

6. Emit completion:
   - Emit `IMPLEMENTATION_COMPLETE` and continue to the next step in the workflow — do not stop.

## Rules

- Never add features, refactor, or clean up code beyond what the ACs require
- Never guess at a third-party API — check the actual package or its documentation
- If you realize an AC cannot be met as written, stop and emit `WORKFLOW_BLOCKED: AC <index> cannot be satisfied — <reason>` rather than silently changing scope
