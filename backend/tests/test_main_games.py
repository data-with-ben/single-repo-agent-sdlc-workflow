from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import Game, ObjectiveResult, Season, Team, User

GAME_DATETIME = datetime(2026, 7, 6, 9, 0, 0)


@pytest.fixture()
def db_and_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'games_test.db'}")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    session = TestSessionLocal()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    admin = User(
        display_name="Admin",
        email="admin@example.com",
        roles=["admin"],
        created_at=now,
        status="active",
    )
    consultant = User(
        display_name="Priya K.",
        email="priya@example.com",
        roles=["consultant"],
        created_at=now,
        status="active",
    )
    session.add_all([admin, consultant])
    session.commit()

    season = Season(
        name="S",
        start_date=GAME_DATETIME,
        end_date=GAME_DATETIME,
        status="active",
        team_size=3,
    )
    session.add(season)
    session.flush()
    home_team = Team(season_id=season.id, name="Sandbaggers")
    away_team = Team(season_id=season.id, name="Scope Creep")
    session.add_all([home_team, away_team])
    session.flush()

    hidden_game = Game(
        game_date=GAME_DATETIME,
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        home_score=25.0,
        away_score=15.0,
        revealed=False,
        state="in_progress",
    )
    revealed_game = Game(
        game_date=GAME_DATETIME,
        season_id=season.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        home_score=30.0,
        away_score=10.0,
        revealed=True,
        state="final",
    )
    session.add_all([hidden_game, revealed_game])
    session.commit()
    session.refresh(revealed_game)

    session.add(
        ObjectiveResult(
            game_id=revealed_game.id,
            game_date=GAME_DATETIME,
            consultant_id=consultant.id,
            team_id=home_team.id,
            projected_by_11=True,
            logged_same_day=True,
            eod_update=False,
            perfect_day=False,
            points=20,
        )
    )
    session.commit()
    session.refresh(admin)
    session.refresh(consultant)
    session.refresh(hidden_game)
    session.refresh(revealed_game)

    yield TestClient(app), admin, consultant, hidden_game, revealed_game

    app.dependency_overrides.clear()
    session.close()


class TestListGamesVisibility:
    def test_non_admin_does_not_see_hidden_game_scores(self, db_and_client):
        client, _admin, consultant, hidden_game, _revealed_game = db_and_client

        response = client.get(
            "/games",
            params={"work_date": "2026-07-06"},
            headers={"X-User-Id": str(consultant.id)},
        )

        assert response.status_code == 200
        body = {g["id"]: g for g in response.json()}
        assert body[hidden_game.id]["home_score"] is None
        assert body[hidden_game.id]["away_score"] is None
        assert body[hidden_game.id]["home_team_name"] == "Sandbaggers"

    def test_admin_sees_hidden_game_scores(self, db_and_client):
        client, admin, _consultant, hidden_game, _revealed_game = db_and_client

        response = client.get(
            "/games",
            params={"work_date": "2026-07-06"},
            headers={"X-User-Id": str(admin.id)},
        )

        body = {g["id"]: g for g in response.json()}
        assert body[hidden_game.id]["home_score"] == 25.0

    def test_everyone_sees_revealed_game_scores(self, db_and_client):
        client, _admin, consultant, _hidden_game, revealed_game = db_and_client

        response = client.get(
            "/games",
            params={"work_date": "2026-07-06"},
            headers={"X-User-Id": str(consultant.id)},
        )

        body = {g["id"]: g for g in response.json()}
        assert body[revealed_game.id]["home_score"] == 30.0


class TestBoxScoreEndpoint:
    def test_non_admin_gets_403_for_hidden_game(self, db_and_client):
        client, _admin, consultant, hidden_game, _revealed_game = db_and_client

        response = client.get(
            f"/games/{hidden_game.id}/box-score",
            headers={"X-User-Id": str(consultant.id)},
        )

        assert response.status_code == 403

    def test_admin_can_see_hidden_game_box_score(self, db_and_client):
        client, admin, _consultant, hidden_game, _revealed_game = db_and_client

        response = client.get(
            f"/games/{hidden_game.id}/box-score",
            headers={"X-User-Id": str(admin.id)},
        )

        assert response.status_code == 200

    def test_revealed_game_box_score_matches_objective_results(self, db_and_client):
        client, _admin, consultant, _hidden_game, revealed_game = db_and_client

        response = client.get(
            f"/games/{revealed_game.id}/box-score",
            headers={"X-User-Id": str(consultant.id)},
        )

        assert response.status_code == 200
        body = response.json()
        home_players = body["home"]["players"]
        assert len(home_players) == 1
        assert home_players[0]["display_name"] == "Priya K."
        assert home_players[0]["points"] == 20
        assert body["star_of_game_consultant_id"] is None  # no losing-team players

    def test_missing_game_returns_404(self, db_and_client):
        client, admin, _consultant, _hidden_game, _revealed_game = db_and_client

        response = client.get(
            "/games/999999/box-score", headers={"X-User-Id": str(admin.id)}
        )

        assert response.status_code == 404
