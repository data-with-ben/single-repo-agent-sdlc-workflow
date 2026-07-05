from datetime import date, datetime

import pytest

from app.models import TimeEntry
from app.objective_engine import compute_objective_results

GAME_DATE = date(2026, 7, 6)


def _entry(
    consultant_id: int = 1,
    client_id: int = 1,
    work_date: datetime = datetime(2026, 7, 6),
    projected_at: datetime | None = None,
    logged_at: datetime | None = None,
    updated_at: datetime | None = None,
    description: str | None = None,
    state: str = "empty",
) -> TimeEntry:
    return TimeEntry(
        consultant_id=consultant_id,
        client_id=client_id,
        work_date=work_date,
        projected_at=projected_at,
        logged_at=logged_at,
        updated_at=updated_at,
        description=description,
        state=state,
    )


PERFECT_DESCRIPTION = "x" * 20


def _perfect_entry(**overrides) -> TimeEntry:
    defaults = dict(
        projected_at=datetime(2026, 7, 6, 9, 0),
        logged_at=datetime(2026, 7, 6, 16, 0),
        updated_at=datetime(2026, 7, 6, 16, 0),
        description=PERFECT_DESCRIPTION,
        state="updated",
    )
    defaults.update(overrides)
    return _entry(**defaults)


class TestPerfectDay:
    def test_all_objectives_met_scores_30_and_perfect_day(self):
        results = compute_objective_results([_perfect_entry()], GAME_DATE, set())
        assert len(results) == 1
        result = results[0]
        assert result.consultant_id == 1
        assert result.game_date == GAME_DATE
        assert result.projected_by_11 is True
        assert result.logged_same_day is True
        assert result.eod_update is True
        assert result.perfect_day is True
        assert result.points == 30


class TestProjectedBy11Boundary:
    def test_exactly_11_00_counts(self):
        entry = _perfect_entry(projected_at=datetime(2026, 7, 6, 11, 0, 0))
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.projected_by_11 is True

    def test_one_second_past_11_00_does_not_count(self):
        entry = _perfect_entry(projected_at=datetime(2026, 7, 6, 11, 0, 1))
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.projected_by_11 is False
        assert result.perfect_day is False

    def test_no_projected_at_does_not_count(self):
        entry = _perfect_entry(projected_at=None)
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.projected_by_11 is False

    def test_projected_on_a_different_day_does_not_count(self):
        entry = _perfect_entry(projected_at=datetime(2026, 7, 5, 9, 0))
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.projected_by_11 is False


class TestLoggedSameDay:
    def test_logged_on_a_later_day_does_not_count(self):
        entry = _perfect_entry(logged_at=datetime(2026, 7, 7, 10, 0))
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.logged_same_day is False

    def test_no_logged_at_does_not_count(self):
        entry = _perfect_entry(logged_at=None)
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.logged_same_day is False

    def test_logged_late_in_the_day_still_counts(self):
        # Section 5: loggedAt need only be on workDate, no hour cutoff.
        entry = _perfect_entry(logged_at=datetime(2026, 7, 6, 23, 59))
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.logged_same_day is True


class TestEodUpdateBoundary:
    def test_description_at_19_chars_does_not_count(self):
        entry = _perfect_entry(description="x" * 19)
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.eod_update is False
        assert result.perfect_day is False

    def test_description_at_20_chars_counts(self):
        entry = _perfect_entry(description="x" * 20)
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.eod_update is True

    def test_exactly_15_00_counts(self):
        entry = _perfect_entry(updated_at=datetime(2026, 7, 6, 15, 0, 0))
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.eod_update is True

    def test_one_second_before_15_00_does_not_count(self):
        entry = _perfect_entry(updated_at=datetime(2026, 7, 6, 14, 59, 59))
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.eod_update is False

    def test_no_description_does_not_count(self):
        entry = _perfect_entry(description=None)
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.eod_update is False


class TestMixedMultiClientDay:
    def test_one_slot_failing_projection_fails_the_whole_days_objective(self):
        good = _perfect_entry(client_id=1)
        late = _perfect_entry(client_id=2, projected_at=datetime(2026, 7, 6, 13, 0))
        result = compute_objective_results([good, late], GAME_DATE, set())[0]
        assert result.projected_by_11 is False
        assert result.logged_same_day is True
        assert result.eod_update is True
        assert result.perfect_day is False
        assert result.points == 15

    def test_all_slots_meeting_objectives_scores_perfect_day(self):
        first = _perfect_entry(client_id=1)
        second = _perfect_entry(client_id=2)
        result = compute_objective_results([first, second], GAME_DATE, set())[0]
        assert result.perfect_day is True
        assert result.points == 30


class TestNoAssignedWork:
    def test_consultant_with_no_entries_for_game_date_is_omitted(self):
        entry = _perfect_entry(consultant_id=1, work_date=datetime(2026, 7, 5))
        results = compute_objective_results([entry], GAME_DATE, set())
        assert results == []

    def test_empty_entries_list_returns_empty_results(self):
        assert compute_objective_results([], GAME_DATE, set()) == []


class TestPtoExclusion:
    def test_consultant_on_pto_is_omitted_even_with_perfect_entries(self):
        entry = _perfect_entry(consultant_id=1)
        results = compute_objective_results([entry], GAME_DATE, {1})
        assert results == []

    def test_all_pto_date_returns_empty_results(self):
        entries = [
            _perfect_entry(consultant_id=1),
            _perfect_entry(consultant_id=2),
        ]
        results = compute_objective_results(entries, GAME_DATE, {1, 2})
        assert results == []

    def test_only_non_pto_consultants_are_scored(self):
        entries = [
            _perfect_entry(consultant_id=1),
            _perfect_entry(consultant_id=2),
        ]
        results = compute_objective_results(entries, GAME_DATE, {1})
        assert len(results) == 1
        assert results[0].consultant_id == 2


class TestAntiGamingIgnoresState:
    def test_state_empty_with_full_timestamps_still_scores_correctly(self):
        # Anti-gaming (AC #3): scoring must read only transition timestamps,
        # never the cached `state` field, which could be stale or wrong.
        entry = _perfect_entry(state="empty")
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.perfect_day is True
        assert result.points == 30

    def test_state_updated_with_no_timestamps_scores_zero(self):
        entry = _entry(state="updated")
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.points == 0
        assert result.perfect_day is False


class TestEntriesFilteredToGameDate:
    def test_entries_for_other_dates_are_ignored(self):
        other_day = _perfect_entry(work_date=datetime(2026, 7, 5))
        results = compute_objective_results([other_day], GAME_DATE, set())
        assert results == []

    def test_mixed_dates_only_scores_the_requested_date(self):
        today = _perfect_entry(consultant_id=1)
        other_day = _perfect_entry(consultant_id=1, work_date=datetime(2026, 7, 5))
        results = compute_objective_results([today, other_day], GAME_DATE, set())
        assert len(results) == 1


class TestPointsCap:
    @pytest.mark.parametrize(
        ("projected", "logged", "eod", "expected_points"),
        [
            (True, True, True, 30),
            (True, True, False, 20),
            (True, False, False, 10),
            (False, False, False, 0),
        ],
    )
    def test_points_total_matches_objectives_met(
        self, projected, logged, eod, expected_points
    ):
        entry = _perfect_entry(
            projected_at=datetime(2026, 7, 6, 9, 0) if projected else None,
            logged_at=datetime(2026, 7, 6, 16, 0) if logged else None,
            updated_at=datetime(2026, 7, 6, 16, 0) if eod else None,
            description=PERFECT_DESCRIPTION if eod else None,
        )
        result = compute_objective_results([entry], GAME_DATE, set())[0]
        assert result.points == expected_points
