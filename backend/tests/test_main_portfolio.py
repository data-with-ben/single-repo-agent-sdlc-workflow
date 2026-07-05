from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.models import User, Wallet
from app.trading import OWNERSHIP_CAP_SHARES

NOW = datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture()
def db_and_client(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'portfolio_endpoint_test.db'}")
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
    buyer = User(
        display_name="Buyer",
        email="buyer@example.com",
        roles=["consultant"],
        created_at=NOW,
        status="active",
    )
    consultant = User(
        display_name="Consultant",
        email="consultant@example.com",
        roles=["consultant"],
        created_at=NOW,
        status="active",
    )
    session.add_all([buyer, consultant])
    session.commit()
    session.add(Wallet(user_id=buyer.id, balance=1000.0))
    session.commit()
    session.refresh(buyer)
    session.refresh(consultant)

    yield TestClient(app), buyer, consultant

    app.dependency_overrides.clear()
    session.close()


class TestGetMyPortfolio:
    def test_returns_bundled_shape(self, db_and_client):
        client, buyer, _consultant = db_and_client

        response = client.get(
            "/me/portfolio", headers={"X-User-Id": str(buyer.id)}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["wallet_balance"] == 1000.0
        assert body["holdings"] == []
        assert body["dividends"] == []
        assert isinstance(body["market_movers"], list)


class TestListExchange:
    def test_lists_consultants_available_to_browse_and_buy(self, db_and_client):
        client, buyer, consultant = db_and_client

        response = client.get("/exchange", headers={"X-User-Id": str(buyer.id)})

        assert response.status_code == 200
        body = response.json()
        consultant_ids = {row["consultant_id"] for row in body}
        assert consultant.id in consultant_ids


class TestTradeBuy:
    def test_successful_buy_debits_wallet(self, db_and_client):
        client, buyer, consultant = db_and_client

        response = client.post(
            "/trade/buy",
            json={"consultant_id": consultant.id, "shares": 5},
            headers={"X-User-Id": str(buyer.id)},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["side"] == "buy"
        assert body["shares"] == 5

        portfolio = client.get(
            "/me/portfolio", headers={"X-User-Id": str(buyer.id)}
        ).json()
        assert portfolio["wallet_balance"] < 1000.0
        assert len(portfolio["holdings"]) == 1

    def test_ownership_cap_rejected_with_400(self, db_and_client):
        client, buyer, consultant = db_and_client

        response = client.post(
            "/trade/buy",
            json={"consultant_id": consultant.id, "shares": OWNERSHIP_CAP_SHARES + 1},
            headers={"X-User-Id": str(buyer.id)},
        )

        assert response.status_code == 400
        assert "ownership cap" in response.json()["detail"]

    def test_insufficient_balance_rejected_with_400(self, db_and_client):
        client, buyer, consultant = db_and_client

        response = client.post(
            "/trade/buy",
            json={"consultant_id": consultant.id, "shares": 100000},
            headers={"X-User-Id": str(buyer.id)},
        )

        assert response.status_code == 400
        assert "insufficient" in response.json()["detail"]


class TestTradeSell:
    def test_successful_sell_credits_wallet(self, db_and_client):
        client, buyer, consultant = db_and_client
        client.post(
            "/trade/buy",
            json={"consultant_id": consultant.id, "shares": 5},
            headers={"X-User-Id": str(buyer.id)},
        )
        balance_after_buy = client.get(
            "/me/portfolio", headers={"X-User-Id": str(buyer.id)}
        ).json()["wallet_balance"]

        response = client.post(
            "/trade/sell",
            json={"consultant_id": consultant.id, "shares": 2},
            headers={"X-User-Id": str(buyer.id)},
        )

        assert response.status_code == 200
        portfolio = client.get(
            "/me/portfolio", headers={"X-User-Id": str(buyer.id)}
        ).json()
        assert portfolio["wallet_balance"] > balance_after_buy
        assert portfolio["holdings"][0]["shares"] == 3

    def test_oversell_rejected_with_400(self, db_and_client):
        client, buyer, consultant = db_and_client

        response = client.post(
            "/trade/sell",
            json={"consultant_id": consultant.id, "shares": 1},
            headers={"X-User-Id": str(buyer.id)},
        )

        assert response.status_code == 400
        assert "sell" in response.json()["detail"]
