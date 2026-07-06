from datetime import date

from app.models import Game
from app.objective_engine import ObjectiveResult
from app.team_scoring import resolve_games

GAME_DATE = date(2026, 7, 6)


def _game(game_id: int, home_team_id: int, away_team_id: int) -> Game:
    return Game(
        id=game_id,
        game_date=GAME_DATE,
        season_id=1,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
    )


def _result(
    consultant_id: int, points: int, projected_by_11: bool = False
) -> ObjectiveResult:
    return ObjectiveResult(
        consultant_id=consultant_id,
        game_date=GAME_DATE,
        projected_by_11=projected_by_11,
        logged_same_day=True,
        eod_update=False,
        perfect_day=False,
        points=points,
    )


class TestNormalization:
    def test_normalized_score_is_average_of_present_members_points(self):
        results = [_result(1, 30), _result(2, 20), _result(3, 10)]
        memberships = {1: {1, 2, 3}, 2: {4}}
        games = [_game(1, home_team_id=1, away_team_id=2)]
        # away team has no results at all -> postponed, but we only assert
        # on home's normalization here.
        resolved = resolve_games(results + [_result(4, 0)], memberships, games)
        assert resolved[0].home_score == 20.0  # (30+20+10)/3


class TestThreeVsFiveFairness:
    def test_equal_per_member_points_produce_equal_normalized_scores(self):
        # SPEC.md Section 7: normalization keeps 3-person teams competitive
        # vs 5-person teams, despite very different raw sums (60 vs 100).
        three_team = [_result(i, 20) for i in range(1, 4)]
        five_team = [_result(i, 20) for i in range(101, 106)]
        memberships = {1: {1, 2, 3}, 2: {101, 102, 103, 104, 105}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(three_team + five_team, memberships, games)[0]

        assert resolved.home_score == resolved.away_score == 20.0
        assert resolved.is_draw is True


class TestTeamBonus:
    def test_bonus_applied_when_all_present_members_hit_11am(self):
        home = [
            _result(1, 10, projected_by_11=True),
            _result(2, 10, projected_by_11=True),
        ]
        away = [_result(3, 10, projected_by_11=False)]
        memberships = {1: {1, 2}, 2: {3}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(home + away, memberships, games)[0]

        assert resolved.home_bonus_applied is True
        assert resolved.home_score == 10.0 + 10  # normalized(10) + bonus(10)
        assert resolved.away_bonus_applied is False
        assert resolved.away_score == 10.0

    def test_bonus_not_applied_when_one_present_member_misses_11am(self):
        home = [
            _result(1, 10, projected_by_11=True),
            _result(2, 10, projected_by_11=False),
        ]
        away = [_result(3, 10, projected_by_11=True)]
        memberships = {1: {1, 2}, 2: {3}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(home + away, memberships, games)[0]

        assert resolved.home_bonus_applied is False
        assert resolved.home_score == 10.0


class TestWinnerAndDraw:
    def test_higher_score_wins(self):
        home = [_result(1, 30)]
        away = [_result(2, 10)]
        memberships = {1: {1}, 2: {2}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(home + away, memberships, games)[0]

        assert resolved.winner_team_id == 1
        assert resolved.is_draw is False

    def test_away_team_can_win(self):
        home = [_result(1, 10)]
        away = [_result(2, 30)]
        memberships = {1: {1}, 2: {2}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(home + away, memberships, games)[0]

        assert resolved.winner_team_id == 2
        assert resolved.is_draw is False

    def test_equal_scores_are_a_draw_not_both_win(self):
        home = [_result(1, 20)]
        away = [_result(2, 20)]
        memberships = {1: {1}, 2: {2}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(home + away, memberships, games)[0]

        assert resolved.is_draw is True
        assert resolved.winner_team_id is None


class TestPostponement:
    def test_away_team_entirely_absent_postpones_the_whole_game(self):
        home = [_result(1, 30)]
        memberships = {1: {1}, 2: {2}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(home, memberships, games)[0]

        assert resolved.postponed is True
        assert resolved.home_score is None
        assert resolved.away_score is None
        assert resolved.winner_team_id is None
        assert resolved.is_draw is False

    def test_home_team_entirely_absent_postpones_the_whole_game(self):
        away = [_result(2, 30)]
        memberships = {1: {1}, 2: {2}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(away, memberships, games)[0]

        assert resolved.postponed is True

    def test_both_teams_entirely_absent_postpones_the_whole_game(self):
        memberships = {1: {1}, 2: {2}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games([], memberships, games)[0]

        assert resolved.postponed is True
        assert resolved.winner_team_id is None
        assert resolved.is_draw is False

    def test_team_missing_from_memberships_defaults_to_zero_present_and_postpones(self):
        home = [_result(1, 30)]
        memberships = {1: {1}}  # team 2 has no roster entry at all
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(home, memberships, games)[0]

        assert resolved.postponed is True


class TestByesDoNotAffectOtherGames:
    def test_a_bye_teams_unused_roster_and_results_do_not_perturb_other_games(self):
        home = [_result(1, 30)]
        away = [_result(2, 10)]
        # Team 3 is on a bye this date: it has a roster and even a stray
        # result, but no Game row -- it must not affect the one real game.
        bye_team_result = [_result(3, 999)]
        memberships = {1: {1}, 2: {2}, 3: {3}}
        games = [_game(1, home_team_id=1, away_team_id=2)]

        resolved = resolve_games(home + away + bye_team_result, memberships, games)

        assert len(resolved) == 1
        assert resolved[0].home_score == 30.0
        assert resolved[0].away_score == 10.0
        assert resolved[0].winner_team_id == 1
