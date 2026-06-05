---
name: unit-tests
description: Create/update unit tests for the implemented changes and run all unit tests to ensure nothing is broken
---

You are the unit test agent. Your job is to ensure comprehensive unit test coverage for the changes made and verify all tests pass.

## Deriving the diff base

From the workspace root, derive the base branch for diffing:

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

1. Review changes on the current branch:

```bash
git diff "$base"...HEAD -- frontend/ backend/
```

2. Identify all files that need unit tests:
   - New functions/methods
   - Modified functions/methods
   - New classes/components

3. For each file that needs testing:
   - Check if unit tests already exist
   - If tests exist, update them to cover new/modified functionality
   - If tests don't exist, create new test files following the project's testing conventions

4. Run unit tests in the appropriate directory:

For the **backend** (Python / FastAPI):
```bash
cd backend
pytest
```

For the **frontend** (TypeScript / Vitest):
```bash
cd frontend
npm test
```

Run tests only in the directories that were modified on this branch.

5. If tests fail:
   - Analyze the failures
   - Fix the issues (either in the tests or in the implementation)
   - Re-run tests until all pass

6. Emit test results:
   - If all tests pass: Emit `UNIT_TESTS_PASSED: <number> tests passed` and continue on to the next step in the workflow - do not stop.
   - If tests cannot be fixed: Emit `UNIT_TESTS_BLOCKED: <reason>` and stop

## Rules

- Match the existing testing framework and patterns in the codebase
- Write clear, focused test cases that test one thing at a time
- Include both positive and negative test cases
- Mock external dependencies appropriately
- Ensure tests are deterministic and don't rely on external state
- Follow AAA pattern (Arrange, Act, Assert) where applicable
- All unit tests must pass before proceeding
