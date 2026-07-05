"""Team scoring and game resolution (SPEC.md Section 7).

Pure function, no I/O: `resolve_games` sits between the objective engine
and the not-yet-built nightly reveal job (task-26) in the pipeline named
in SPEC.md Section 10 (objective engine -> team scoring -> game winners ->
write results). It never touches app.models.ObjectiveResult (the
persisted, game_id/team_id-keyed table) -- that table is populated later
by the reveal job using this function's output plus the objective
engine's.

Present members: a team's roster (team_memberships) intersected with the
consultant_ids that actually appear in the given objective_results. The
objective engine already omits PTO and no-assigned-work consultants from
its output, so this intersection directly gives SPEC.md Section 7's
"present member" set with no separate PTO input needed here.

Postponement: SPEC.md Section 7 says "team entirely on PTO -> game
postponed/voided". This module reads that as applying to the whole game
whenever *either* side has zero present members, not only when both do --
a defensible, direct reading of the sentence (a team, singular, triggers
game, the whole matchup), documented here as a resolved interpretation
per the hostile plan review's note. A postponed game has no scores and no
winner/draw (winner_team_id=None, is_draw=False).

Byes: a team with no scheduled Game for a date (SPEC.md Section 7: odd
team count -> one bye) simply never appears in the `games` input for that
date. Each game is resolved independently, so a bye team's absence cannot
affect any other game's computed scores.

Draw handling: SPEC.md Section 11, item 1 lists this as an explicitly
open decision with only a stated preference ("recommend draw flag"), not
a recorded resolution. This module adopts that stated preference as the
resolution, since it is the only concrete direction given anywhere in the
docs -- flagged for hostile review, same as the objective engine's
working-slot interpretation.
"""

from dataclasses import dataclass

from app.models import Game
from app.objective_engine import ObjectiveResult

TEAM_BONUS = 10


@dataclass
class GameResult:
    game_id: int
    home_team_id: int
    away_team_id: int
    home_score: float | None
    away_score: float | None
    home_bonus_applied: bool
    away_bonus_applied: bool
    winner_team_id: int | None
    is_draw: bool
    postponed: bool


def _present_results(
    team_id: int,
    objective_results: list[ObjectiveResult],
    team_memberships: dict[int, set[int]],
) -> list[ObjectiveResult]:
    roster = team_memberships.get(team_id, set())
    return [r for r in objective_results if r.consultant_id in roster]


def _team_score(present: list[ObjectiveResult]) -> tuple[float, bool]:
    total_points = sum(r.points for r in present)
    normalized = total_points / len(present)
    bonus_applied = all(r.projected_by_11 for r in present)
    score = normalized + (TEAM_BONUS if bonus_applied else 0)
    return score, bonus_applied


def resolve_games(
    objective_results: list[ObjectiveResult],
    team_memberships: dict[int, set[int]],
    games: list[Game],
) -> list[GameResult]:
    results = []
    for game in games:
        home_present = _present_results(
            game.home_team_id, objective_results, team_memberships
        )
        away_present = _present_results(
            game.away_team_id, objective_results, team_memberships
        )

        if not home_present or not away_present:
            results.append(
                GameResult(
                    game_id=game.id,
                    home_team_id=game.home_team_id,
                    away_team_id=game.away_team_id,
                    home_score=None,
                    away_score=None,
                    home_bonus_applied=False,
                    away_bonus_applied=False,
                    winner_team_id=None,
                    is_draw=False,
                    postponed=True,
                )
            )
            continue

        home_score, home_bonus = _team_score(home_present)
        away_score, away_bonus = _team_score(away_present)

        if home_score > away_score:
            winner_team_id: int | None = game.home_team_id
            is_draw = False
        elif away_score > home_score:
            winner_team_id = game.away_team_id
            is_draw = False
        else:
            winner_team_id = None
            is_draw = True

        results.append(
            GameResult(
                game_id=game.id,
                home_team_id=game.home_team_id,
                away_team_id=game.away_team_id,
                home_score=home_score,
                away_score=away_score,
                home_bonus_applied=home_bonus,
                away_bonus_applied=away_bonus,
                winner_team_id=winner_team_id,
                is_draw=is_draw,
                postponed=False,
            )
        )

    return results
