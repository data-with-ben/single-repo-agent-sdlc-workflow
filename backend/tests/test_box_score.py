from datetime import datetime

from app.box_score import box_score_for_game, game_summary, star_of_game
from app.models import Game, ObjectiveResult

GAME_DATETIME = datetime(2026, 7, 6, 9, 0, 0)


def _game(revealed, state="scheduled", home_score=None, away_score=None):
    return Game(
        id=1,
        game_date=GAME_DATETIME,
        season_id=1,
        home_team_id=10,
        away_team_id=20,
        home_score=home_score,
        away_score=away_score,
        revealed=revealed,
        state=state,
    )


def _result(consultant_id, team_id, points=10, projected_by_11=True):
    return ObjectiveResult(
        game_id=1,
        game_date=GAME_DATETIME,
        consultant_id=consultant_id,
        team_id=team_id,
        projected_by_11=projected_by_11,
        logged_same_day=True,
        eod_update=False,
        perfect_day=False,
        points=points,
    )


class TestGameSummaryVisibility:
    def test_hides_scores_for_non_admin_before_reveal(self):
        game = _game(revealed=False, state="scheduled")

        summary = game_summary(game, "Home", "Away", is_admin=False)

        assert summary["home_score"] is None
        assert summary["away_score"] is None
        assert summary["home_team_name"] == "Home"
        assert summary["away_team_name"] == "Away"

    def test_shows_scores_for_admin_before_reveal(self):
        game = _game(
            revealed=False, state="in_progress", home_score=12.0, away_score=8.0
        )

        summary = game_summary(game, "Home", "Away", is_admin=True)

        assert summary["home_score"] == 12.0
        assert summary["away_score"] == 8.0

    def test_shows_scores_for_non_admin_after_reveal(self):
        game = _game(revealed=True, state="final", home_score=20.0, away_score=15.0)

        summary = game_summary(game, "Home", "Away", is_admin=False)

        assert summary["home_score"] == 20.0
        assert summary["away_score"] == 15.0


class TestStarOfGame:
    def test_top_scorer_on_losing_team_wins(self):
        results = [_result(1, 20, points=10), _result(2, 20, points=25)]

        assert star_of_game(results) == 2

    def test_ties_broken_by_lowest_consultant_id(self):
        results = [_result(5, 20, points=10), _result(1, 20, points=10)]

        assert star_of_game(results) == 1

    def test_empty_losing_team_returns_none(self):
        assert star_of_game([]) is None


class TestBoxScoreForGame:
    def test_matches_the_computed_objective_results(self):
        game = _game(revealed=True, state="final", home_score=30.0, away_score=10.0)
        results = [
            _result(1, 10, points=20),
            _result(2, 10, points=10),
            _result(3, 20, points=5),
            _result(4, 20, points=5),
        ]
        names = {1: "Alice", 2: "Bob", 3: "Carl", 4: "Dana"}

        box = box_score_for_game(game, results, "Home", "Away", names)

        assert box.game_id == 1
        assert {p.consultant_id for p in box.home.players} == {1, 2}
        assert {p.consultant_id for p in box.away.players} == {3, 4}
        alice = next(p for p in box.home.players if p.consultant_id == 1)
        assert alice.display_name == "Alice"
        assert alice.points == 20
        assert box.home.normalized_score == (20 + 10) / 2 + 10  # team bonus applied

    def test_star_of_game_is_the_top_scorer_on_the_losing_team(self):
        game = _game(revealed=True, state="final", home_score=30.0, away_score=10.0)
        results = [
            _result(1, 10, points=20),
            _result(2, 10, points=10),
            _result(3, 20, points=5),
            _result(4, 20, points=8),
        ]
        names = {1: "Alice", 2: "Bob", 3: "Carl", 4: "Dana"}

        box = box_score_for_game(game, results, "Home", "Away", names)

        assert box.star_of_game_consultant_id == 4

    def test_star_of_game_when_home_team_loses(self):
        game = _game(revealed=True, state="final", home_score=10.0, away_score=30.0)
        results = [
            _result(1, 10, points=5),
            _result(2, 10, points=8),
            _result(3, 20, points=20),
            _result(4, 20, points=10),
        ]
        names = {1: "Alice", 2: "Bob", 3: "Carl", 4: "Dana"}

        box = box_score_for_game(game, results, "Home", "Away", names)

        assert box.star_of_game_consultant_id == 2

    def test_draw_has_no_star_of_game(self):
        game = _game(revealed=True, state="final", home_score=20.0, away_score=20.0)
        results = [_result(1, 10, points=20), _result(2, 20, points=20)]
        names = {1: "Alice", 2: "Bob"}

        box = box_score_for_game(game, results, "Home", "Away", names)

        assert box.star_of_game_consultant_id is None

    def test_postponed_game_has_no_star_of_game(self):
        game = _game(revealed=True, state="final", home_score=None, away_score=None)
        results = []
        names = {}

        box = box_score_for_game(game, results, "Home", "Away", names)

        assert box.star_of_game_consultant_id is None
        assert box.home.players == []
