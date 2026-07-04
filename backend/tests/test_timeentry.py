from datetime import datetime, timedelta

import pytest

from app.models import TimeEntry
from app.timeentry import IllegalTransitionError, eod_update, log, project


def _new_entry() -> TimeEntry:
    return TimeEntry(
        consultant_id=1,
        client_id=1,
        work_date=datetime(2026, 7, 6),
        state="empty",
    )


def test_project_sets_exactly_the_spec_fields():
    entry = _new_entry()
    at = datetime(2026, 7, 6, 9, 0)

    project(entry, planned_hours=8, client_id=2, at=at)

    assert entry.planned_hours == 8
    assert entry.client_id == 2
    assert entry.projected_at == at
    assert entry.state == "projected"


def test_log_sets_exactly_the_spec_fields():
    entry = _new_entry()
    at = datetime(2026, 7, 6, 16, 0)

    log(entry, actual_hours=7.5, at=at)

    assert entry.actual_hours == 7.5
    assert entry.logged_at == at
    assert entry.state == "logged"


def test_eod_update_sets_exactly_the_spec_fields():
    entry = _new_entry()
    at = datetime(2026, 7, 6, 16, 30)

    eod_update(entry, description="Finished the report.", at=at)

    assert entry.description == "Finished the report."
    assert entry.updated_at == at
    assert entry.state == "updated"


def test_skipping_states_is_allowed():
    entry = _new_entry()
    eod_update(entry, description="Straight to EOD.", at=datetime(2026, 7, 6, 17, 0))

    assert entry.state == "updated"
    assert entry.planned_hours is None
    assert entry.actual_hours is None


def test_first_submitted_at_is_set_once_and_never_changes():
    entry = _new_entry()
    first_at = datetime(2026, 7, 6, 9, 0)
    later_at = datetime(2026, 7, 6, 16, 0)

    project(entry, planned_hours=8, client_id=2, at=first_at)
    assert entry.first_submitted_at == first_at

    log(entry, actual_hours=8, at=later_at)
    assert entry.first_submitted_at == first_at


def test_project_is_rejected_once_state_has_moved_past_empty():
    entry = _new_entry()
    log(entry, actual_hours=8, at=datetime(2026, 7, 6, 16, 0))

    with pytest.raises(IllegalTransitionError):
        project(entry, planned_hours=8, client_id=2, at=datetime(2026, 7, 6, 17, 0))


def test_log_revision_updates_actual_hours_but_not_logged_at():
    entry = _new_entry()
    first_log_at = datetime(2026, 7, 6, 16, 0)
    revision_at = datetime(2026, 7, 6, 18, 0)

    log(entry, actual_hours=7, at=first_log_at)
    eod_update(entry, description="Wrapped up.", at=datetime(2026, 7, 6, 17, 0))
    log(entry, actual_hours=7.5, at=revision_at)

    assert entry.actual_hours == 7.5
    assert entry.logged_at == first_log_at


def test_eod_update_revision_overwrites_description_and_updated_at():
    entry = _new_entry()
    eod_update(entry, description="First draft.", at=datetime(2026, 7, 6, 15, 0))
    eod_update(entry, description="Revised.", at=datetime(2026, 7, 6, 15, 30))

    assert entry.description == "Revised."
    assert entry.updated_at == datetime(2026, 7, 6, 15, 30)


def test_anti_gaming_invariant_a_later_fix_does_not_backdate_logged_at():
    """AC #5: a later fix to an entry must not backdate its scoring
    objective -- loggedAt (the anti-gaming timestamp the objective engine
    reads) is fixed at first submission, not the latest revision.
    """
    entry = _new_entry()
    day_one = datetime(2026, 7, 6, 16, 0)
    log(entry, actual_hours=6, at=day_one)

    much_later = day_one + timedelta(days=3)
    log(entry, actual_hours=8, at=much_later)

    assert entry.logged_at == day_one
    assert entry.actual_hours == 8
