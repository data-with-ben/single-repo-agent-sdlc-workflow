"""Scoreboard and box score (SPEC.md Section 9 screen 4, wireframe 4).

Pure functions, no I/O -- mirrors team_scoring.py's shape. Takes persisted
app.models.ObjectiveResult rows (read back from the DB by the caller), not
app.objective_engine.ObjectiveResult (the pure dataclass used upstream in
the reveal pipeline) -- the two classes share a name across modules; this
module only ever deals with the persisted, already-written rows.

Admin visibility (SPEC.md Section 11 item 3, recommend yes/admin-only):
callers gate score visibility themselves (game_summary's is_admin
parameter, and the box-score endpoint's 403 for a non-revealed game); this
module does not know about roles or HTTP.

Star of the game: computed independently from dividends.py's
compute_dividend_awards, rather than reusing it, since that function skips
creating a star_of_game award entirely when the earning consultant has no
shareholders -- the box score must show the star of the game regardless of
share ownership. Same tie-break (top points, ties broken by lowest
consultant_id) for consistency with dividends.py, duplicated rather than
imported (same precedent as dividends.py duplicating team_scoring's
_present_results).
"""

from dataclasses import dataclass

from app.models import Game, ObjectiveResult

TEAM_BONUS = 10


@dataclass
class PlayerLine:
    consultant_id: int
    display_name: str
    projected_by_11: bool
    logged_same_day: bool
    eod_update: bool
    points: int


@dataclass
class TeamBoxScore:
    team_id: int
    team_name: str
    normalized_score: float
    team_bonus_applied: bool
    players: list[PlayerLine]


@dataclass
class BoxScore:
    game_id: int
    home: TeamBoxScore
    away: TeamBoxScore
    star_of_game_consultant_id: int | None


def game_summary(
    game: Game, home_team_name: str, away_team_name: str, is_admin: bool
) -> dict:
    show_scores = game.revealed or is_admin
    return {
        "id": game.id,
        "game_date": game.game_date.date().isoformat(),
        "home_team_name": home_team_name,
        "away_team_name": away_team_name,
        "revealed": game.revealed,
        "state": game.state,
        "home_score": game.home_score if show_scores else None,
        "away_score": game.away_score if show_scores else None,
    }


def _team_box_score(
    team_id: int,
    team_name: str,
    results: list[ObjectiveResult],
    display_names: dict[int, str],
) -> TeamBoxScore:
    total_points = sum(r.points for r in results)
    normalized = total_points / len(results) if results else 0.0
    bonus_applied = bool(results) and all(r.projected_by_11 for r in results)
    return TeamBoxScore(
        team_id=team_id,
        team_name=team_name,
        normalized_score=normalized + (TEAM_BONUS if bonus_applied else 0),
        team_bonus_applied=bonus_applied,
        players=[
            PlayerLine(
                consultant_id=r.consultant_id,
                display_name=display_names.get(r.consultant_id, ""),
                projected_by_11=r.projected_by_11,
                logged_same_day=r.logged_same_day,
                eod_update=r.eod_update,
                points=r.points,
            )
            for r in results
        ],
    )


def star_of_game(losing_team_results: list[ObjectiveResult]) -> int | None:
    if not losing_team_results:
        return None
    star = min(losing_team_results, key=lambda r: (-r.points, r.consultant_id))
    return star.consultant_id


def box_score_for_game(
    game: Game,
    objective_results: list[ObjectiveResult],
    home_team_name: str,
    away_team_name: str,
    display_names: dict[int, str],
) -> BoxScore:
    home_results = [r for r in objective_results if r.team_id == game.home_team_id]
    away_results = [r for r in objective_results if r.team_id == game.away_team_id]

    home = _team_box_score(
        game.home_team_id, home_team_name, home_results, display_names
    )
    away = _team_box_score(
        game.away_team_id, away_team_name, away_results, display_names
    )

    star_consultant_id: int | None = None
    if game.home_score is not None and game.away_score is not None:
        if game.home_score > game.away_score:
            star_consultant_id = star_of_game(away_results)
        elif game.away_score > game.home_score:
            star_consultant_id = star_of_game(home_results)
        # a draw has no losing team, so no star of the game

    return BoxScore(
        game_id=game.id,
        home=home,
        away=away,
        star_of_game_consultant_id=star_consultant_id,
    )
