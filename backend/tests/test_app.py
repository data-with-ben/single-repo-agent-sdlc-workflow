from app.main import app


def test_app_exists():
    assert app.title == "Backend API"
