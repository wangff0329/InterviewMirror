from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_login_and_duplicate_email(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    client = TestClient(app)
    email = f"test-{uuid4().hex}@example.com"
    register_response = client.post("/api/auth/register", json={"email": email.upper(), "password": "password123"})
    assert register_response.status_code == 201
    assert register_response.json()["user"]["email"] == email
    assert register_response.json()["access_token"]

    duplicate_response = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert duplicate_response.status_code == 409

    login_response = client.post("/api/auth/login", json={"email": email.upper(), "password": "password123"})
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email
