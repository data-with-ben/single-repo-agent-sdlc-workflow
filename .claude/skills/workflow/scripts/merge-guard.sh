#!/usr/bin/env bash
#
# Workflow Step 12: Merge guard (scope check).
#
# Compares the current branch's diff against the task's `modified_files` field.
# Exits non-zero and prints WORKFLOW_BLOCKED if it detects out-of-scope changes.
#
# Usage:
#   .claude/skills/workflow/scripts/merge-guard.sh <task-id>
#
# Exit codes:
#   0  All changes in scope.
#   1  Repo is on main/master/develop (feature branch required).
#   2  Out-of-scope files detected.
#   3  Argument or environment error.
#
# A file is considered IN scope if any of:
#   - It appears in the task's `modified_files`
#   - It's a routine artifact: test files, e2e test-results/, lockfiles
#   - It matches the patterns listed in IGNORE_PATTERNS below
#
# The script is intended to be invoked from the workspace root.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: merge-guard.sh <task-id>" >&2
  exit 3
fi

task_id="$1"

# Repo-relative ignore patterns (extended regex). Any changed file matching one
# of these is treated as a routine artifact and not flagged as scope creep.
IGNORE_PATTERNS=(
  '(^|/)test-results/'
  '(^|/)playwright-report/'
  '(^|/)package-lock\.json$'
  '(^|/)bun\.lockb$'
  '(^|/)yarn\.lock$'
  '(^|/)pnpm-lock\.yaml$'
  '(^|/)poetry\.lock$'
  '(^|/)tests?/'
  '\.spec\.(ts|tsx|js|jsx)$'
  '_test\.py$'
  '/test_[^/]+\.py$'
)

is_ignored() {
  local f="$1"
  for pat in "${IGNORE_PATTERNS[@]}"; do
    if [[ "$f" =~ $pat ]]; then
      return 0
    fi
  done
  return 1
}

# Precondition: must be on a feature branch.
current_branch="$(git branch --show-current)"
case "$current_branch" in
  main|master|develop)
    echo "WORKFLOW_BLOCKED: workflow running on $current_branch branch — feature branch required"
    exit 1
    ;;
esac

# Derive the diff base.
base="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [ -z "$base" ]; then
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    base="origin/main"
  else
    base="main"
  fi
fi

# Read modified_files from the task. The `--plain` renderer prints this as a
# single "Modified files: a, b, c" line, not a YAML-style block.
mapfile -t task_scope < <(
  cd backlog
  backlog task "$task_id" --plain |
    sed -n 's/^Modified files: //p' |
    tr ',' '\n' |
    sed 's/^[[:space:]]*//; s/[[:space:]]*$//'
)

# Build a set of in-scope paths for quick lookup.
declare -A scope_set
for f in "${task_scope[@]}"; do
  scope_set["$f"]=1
done

# Check if the branch has any commits ahead of base.
if ! git rev-parse --verify "$base" >/dev/null 2>&1; then
  echo "MERGE_GUARD_PASSED: base '$base' not found — nothing to inspect"
  exit 0
fi

ahead="$(git rev-list --count "$base..HEAD" 2>/dev/null || echo 0)"
if [ "$ahead" -eq 0 ]; then
  echo "MERGE_GUARD_PASSED: no commits ahead of $base"
  exit 0
fi

# Compare changed files against task scope.
out_of_scope=()
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if is_ignored "$f"; then
    continue
  fi
  if [ -n "${scope_set[$f]+x}" ]; then
    continue
  fi
  out_of_scope+=("$f")
done < <(git diff "$base"..HEAD --name-only)

if [ "${#out_of_scope[@]}" -gt 0 ]; then
  printf 'WORKFLOW_BLOCKED: scope creep detected — files outside task scope:\n'
  printf '  - %s\n' "${out_of_scope[@]}"
  exit 2
fi

echo "MERGE_GUARD_PASSED: all changes within task scope"
exit 0
