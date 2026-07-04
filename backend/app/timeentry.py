"""TimeEntry state machine (SPEC.md Section 5).

    empty --project()--> projected --log()--> logged --eodUpdate()--> updated

`state` tracks the highest transition ever reached and is monotonically
non-decreasing regardless of which function is called first -- skipping
states is allowed (e.g. calling eod_update() straight from empty jumps
state to "updated"), matching SPEC.md's "skipping states is allowed but
forfeits the skipped objectives".

project() is first-submission-only: SPEC.md gives eodUpdate() explicit
"sets/revises" language but never says project() can be revised, so
calling it a second time (once state has moved past "empty") is the
illegal transition AC #3 requires -- rejected via IllegalTransitionError.

log() may be called again after reaching "logged"/"updated" to revise
actualHours, but loggedAt itself -- SPEC.md calls it "timestamp actuals
first submitted" -- is written once and never changes after.

eod_update() may always be called; it revises description and
overwrites updatedAt every time, per SPEC.md's explicit "write/revise".

first_submitted_at is set on the very first call to any of the three
functions (whichever happens first) and never changes after -- this is
what the anti-gaming objective checks (Section 6) read instead of
mutable current state.
"""

from datetime import datetime

from app.models import TimeEntry

_STATE_ORDER = {"empty": 0, "projected": 1, "logged": 2, "updated": 3}


class IllegalTransitionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _advance_state(entry: TimeEntry, at_least: str) -> None:
    if _STATE_ORDER[at_least] > _STATE_ORDER[entry.state]:
        entry.state = at_least


def _mark_first_submission(entry: TimeEntry, at: datetime) -> None:
    if entry.first_submitted_at is None:
        entry.first_submitted_at = at


def project(
    entry: TimeEntry, planned_hours: float, client_id: int, at: datetime
) -> None:
    if entry.state != "empty":
        raise IllegalTransitionError(
            "Cannot project: entry is already past 'empty' "
            f"(current state: {entry.state})"
        )
    entry.planned_hours = planned_hours
    entry.client_id = client_id
    entry.projected_at = at
    _mark_first_submission(entry, at)
    _advance_state(entry, "projected")


def log(entry: TimeEntry, actual_hours: float, at: datetime) -> None:
    entry.actual_hours = actual_hours
    if entry.logged_at is None:
        entry.logged_at = at
    _mark_first_submission(entry, at)
    _advance_state(entry, "logged")


def eod_update(entry: TimeEntry, description: str, at: datetime) -> None:
    entry.description = description
    entry.updated_at = at
    _mark_first_submission(entry, at)
    _advance_state(entry, "updated")
