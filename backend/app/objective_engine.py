"""Objective scoring engine (SPEC.md Section 6).

Pure function, no I/O: `compute_objective_results` takes already-loaded
TimeEntry rows, the game date being scored, and the set of consultants on
PTO that date, and returns one ObjectiveResult per non-excluded consultant.

Working slot: SPEC.md Section 11 leaves "definition of a working slot" as
an open org-policy decision. This module treats each TimeEntry given for a
consultant on game_date as one working slot -- the function's signature
(TimeEntry[], date, ptoCalendar) has no Assignment[] parameter, so the
caller (the nightly reveal job) is responsible for including one entry per
client a consultant should have worked that day, including still-empty
entries for untouched assignments. A consultant with zero entries for
game_date is neutral (no assigned work) and is omitted from the result.

Anti-gaming (SPEC.md Section 5): only projected_at/logged_at/updated_at/
description are read. entry.state is never consulted, since it is a
cached convenience field that this engine must not trust.

No per-user timezone is stored or passed to this function (a known,
already-documented gap). All comparisons are made directly against the
timestamps' own values, which are naive datetimes that are true UTC
instants throughout this backend -- effectively UTC-as-local, a
documented simplification consistent with the same class of simplification
already used in the frontend (browser local clock as a stand-in) pending a
real per-user timezone field.
"""

from dataclasses import dataclass
from datetime import date, datetime, time

from app.models import TimeEntry

PROJECTION_CUTOFF = time(11, 0)
EOD_CUTOFF = time(15, 0)
MIN_DESCRIPTION_LENGTH = 20
MAX_POINTS = 30


@dataclass
class ObjectiveResult:
    consultant_id: int
    game_date: date
    projected_by_11: bool
    logged_same_day: bool
    eod_update: bool
    perfect_day: bool
    points: int


def _on_date_by_cutoff(
    ts: datetime | None, game_date: date, cutoff: time, *, at_or_before: bool
) -> bool:
    if ts is None or ts.date() != game_date:
        return False
    return ts.time() <= cutoff if at_or_before else ts.time() >= cutoff


def _projected_by_11(entry: TimeEntry, game_date: date) -> bool:
    return _on_date_by_cutoff(
        entry.projected_at, game_date, PROJECTION_CUTOFF, at_or_before=True
    )


def _logged_same_day(entry: TimeEntry, game_date: date) -> bool:
    return entry.logged_at is not None and entry.logged_at.date() == game_date


def _eod_update(entry: TimeEntry, game_date: date) -> bool:
    on_time = _on_date_by_cutoff(
        entry.updated_at, game_date, EOD_CUTOFF, at_or_before=False
    )
    if not on_time:
        return False
    return (
        entry.description is not None
        and len(entry.description) >= MIN_DESCRIPTION_LENGTH
    )


def compute_objective_results(
    entries: list[TimeEntry],
    game_date: date,
    pto_consultant_ids: set[int],
) -> list[ObjectiveResult]:
    slots_by_consultant: dict[int, list[TimeEntry]] = {}
    for entry in entries:
        if entry.work_date.date() != game_date:
            continue
        slots_by_consultant.setdefault(entry.consultant_id, []).append(entry)

    results = []
    for consultant_id, slots in slots_by_consultant.items():
        if consultant_id in pto_consultant_ids:
            continue

        projected_by_11 = all(_projected_by_11(e, game_date) for e in slots)
        logged_same_day = all(_logged_same_day(e, game_date) for e in slots)
        eod_update = all(_eod_update(e, game_date) for e in slots)
        perfect_day = projected_by_11 and logged_same_day and eod_update

        points = (
            (10 if projected_by_11 else 0)
            + (10 if logged_same_day else 0)
            + (5 if eod_update else 0)
            + (5 if perfect_day else 0)
        )

        results.append(
            ObjectiveResult(
                consultant_id=consultant_id,
                game_date=game_date,
                projected_by_11=projected_by_11,
                logged_same_day=logged_same_day,
                eod_update=eod_update,
                perfect_day=perfect_day,
                points=min(points, MAX_POINTS),
            )
        )

    return results
