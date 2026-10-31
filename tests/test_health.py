from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 404  # Error intencional para la demostración
    assert response.json() == {"status": "ok"}


def test_home_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "Exoplanetas" in response.text
