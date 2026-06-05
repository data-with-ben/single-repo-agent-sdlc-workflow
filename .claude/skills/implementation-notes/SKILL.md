---
name: implementation-notes
description: Write comprehensive implementation notes documenting what was done, key decisions, and any relevant context
---

Your job is to document the implementation details for a completed task.

## Deriving the diff base

From the workspace root:

```bash
base="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -z "$base" ]; then
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    base="origin/main"
  else
    base="main"
  fi
fi
```

## Process

1. Review the changes made on the current branch:

```bash
git diff "$base"...HEAD --stat
git log "$base"..HEAD --oneline
```

2. Review the task details to understand the original requirements:

```bash
cd backlog && backlog task <id> --plain
```

3. Write implementation notes that include:

   **What was implemented:**
   - Summary of the changes made
   - List of files modified/created/deleted
   - Key functionality added or modified

   **Key technical decisions:**
   - Architecture or design patterns used
   - Why certain approaches were chosen over alternatives
   - Any trade-offs or limitations

   **Integration points:**
   - How this integrates with existing code
   - Any new dependencies added
   - Configuration changes required

   **Testing coverage:**
   - What tests were added/updated
   - Test coverage metrics if available
   - Manual testing performed

   **Future considerations:**
   - Known limitations or technical debt
   - Potential improvements or optimizations
   - Related work that may be needed

4. Append the implementation notes to the task:

```bash
cd backlog && backlog task edit <id> --append-notes "<implementation notes>"
```

5. Emit completion:
   - Emit `IMPLEMENTATION_NOTES_COMPLETE: notes added to task <id>` and continue on to the next step in the workflow - do not stop.

## Rules

- Be concise but comprehensive
- Focus on "why" decisions were made, not just "what" was done
- Use markdown formatting for readability
- Include specific file paths and line numbers where relevant
- Highlight any breaking changes or migration steps needed
- Document any deviation from the original plan and why
