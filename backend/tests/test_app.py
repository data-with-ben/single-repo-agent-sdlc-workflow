from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_app_exists():
    assert app.title == "Backend API"


def test_read_root_returns_hello_world():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "hello world"}
