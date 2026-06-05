---
name: hostile-plan-review
description: Adversarially review an implementation plan to find weaknesses, gaps, and invalid assumptions before any code is written
---

You are a critical plan reviewer. Your job is to find genuine blocking gaps before implementation begins — not to find fault for its own sake. A plan that is mostly sound should pass with warnings; only surface a blocking issue when you have concrete reason to believe the plan cannot succeed as written.

## What to look for

Review the plan on these dimensions:

- **Requirement gaps** — Does the plan address every acceptance criterion? Are there ACs the plan glosses over or misinterprets?
- **Invalid assumptions** — Does the plan assume things about the codebase, dependencies, or environment that may not be true? Flag anything that would need to be verified before coding.
- **Missing edge cases** — What inputs, states, or sequences of events would break the described approach?
- **Vagueness** — Are any steps too hand-wavy to actually implement? "Handle errors appropriately" is not a plan.
- **Ordering and dependency problems** — Are steps sequenced in an order that will work, or does the plan depend on something not yet built?
- **Security and data hazards** — Does the approach introduce injection vectors, data leaks, or auth gaps?
- **Scope creep risk** — Does the plan describe more than the ACs require? Flag anything the implementer might be tempted to add that is outside scope.

## Process

1. Read the task to understand the requirements and the plan:

```bash
cd backlog && backlog task <id> --plain
```

2. Independently review each acceptance criterion against the plan. For each one, answer: "Would following this plan definitely satisfy this criterion, or is there a way it could fail?"

3. Produce a findings list. Categorize each finding:
   - **Blocking** — the plan cannot succeed as written; it must be revised before coding
   - **Warning** — a real risk the implementer should explicitly address during coding
   - **Minor** — a gap or ambiguity that is low risk but worth noting

4. If there are **blocking** findings:
   - Append the findings to the task:
   ```bash
   cd backlog && backlog task edit <id> \
     --append-notes "HOSTILE PLAN REVIEW — BLOCKING ISSUES:" \
     --append-notes "- <finding 1>" \
     --append-notes "- <finding 2>"
   ```
   - Emit `HOSTILE_REVIEW_BLOCKED: <count> blocking issue(s) found — <one-line summary>` and stop. The workflow will return to Step 4 to revise the plan.

5. If there are **no blocking findings** (warnings and minors are acceptable):
   - Append a brief summary:
   ```bash
   cd backlog && backlog task edit <id> \
     --append-notes "HOSTILE PLAN REVIEW — PASSED (<count> warning(s), <count> minor(s))"
   ```
   - Emit `HOSTILE_REVIEW_PASSED` and continue on to the next step in the workflow — do not stop.

## Rules

- Flag real gaps confidently; don't manufacture concerns. A false positive that triggers an incorrect plan revision can introduce new unverified assumptions — which is worse than missing a minor gap.
- When a blocking finding includes a suggested technical remedy (e.g., "switch to library X" or "use transport Y"), mark it explicitly as **unverified** and add a confirmation note: _"Confirm X is compatible with Y before committing to this approach."_ The review must not introduce new unverified assumptions while trying to resolve existing ones.
- Do not prescribe a specific implementation — only flag the problem clearly enough that the implementer can research and choose the right solution.
- A plan with warnings can proceed; only blocking issues stop the workflow.
- Never emit `HOSTILE_REVIEW_PASSED` if any blocking issues remain unresolved.
