#!/usr/bin/env bash
#
# Append multi-line content to a backlog task's Implementation Notes.
#
# The backlog CLI does not interpret `\n` inside double-quoted arguments — every
# `--append-notes` flag becomes one note line with literal text. This script
# splits its input on real newlines and runs one `--append-notes` per line, so
# you can pass multi-line content without worrying about shell quoting quirks.
#
# Usage:
#   # From a file:
#   .claude/skills/manage-backlog-tasks/scripts/append-notes.sh <task-id> --file notes.md
#
#   # From stdin:
#   printf 'line one\nline two\n' | .claude/skills/manage-backlog-tasks/scripts/append-notes.sh <task-id>
#
#   # From inline string (use a real newline, e.g. via heredoc to a temp file
#   # if your shell harness rejects ANSI-C quoting):
#   .claude/skills/manage-backlog-tasks/scripts/append-notes.sh <task-id> --string "first
#   second"
#
# Empty lines are preserved as blank notes (so paragraphs render correctly).
#
# Exits 0 on success, non-zero if any backlog edit fails.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: append-notes.sh <task-id> [--file PATH | --string TEXT]" >&2
  exit 2
fi

task_id="$1"
shift

content=""
case "${1:-}" in
  --file)
    if [ -z "${2:-}" ]; then
      echo "error: --file requires a path" >&2
      exit 2
    fi
    content="$(cat "$2")"
    ;;
  --string)
    if [ -z "${2:-}" ]; then
      echo "error: --string requires a value" >&2
      exit 2
    fi
    content="$2"
    ;;
  "")
    content="$(cat -)"
    ;;
  *)
    echo "error: unknown argument: $1" >&2
    exit 2
    ;;
esac

if [ -z "$content" ]; then
  echo "error: no content to append" >&2
  exit 2
fi

# Resolve workspace root so the script works regardless of cwd.
workspace_root="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
backlog_path="$workspace_root/backlog"
if [ ! -d "$backlog_path" ]; then
  echo "error: backlog/ directory not found at $backlog_path" >&2
  exit 3
fi

# Build one --append-notes per line.
flags=()
while IFS= read -r line; do
  flags+=(--append-notes "$line")
done <<<"$content"

if [ "${#flags[@]}" -eq 0 ]; then
  echo "error: produced zero notes from input" >&2
  exit 2
fi

(
  cd "$backlog_path"
  backlog task edit "$task_id" "${flags[@]}"
)

echo "APPEND_NOTES_COMPLETE: $((${#flags[@]} / 2)) line(s) appended to task $task_id"
