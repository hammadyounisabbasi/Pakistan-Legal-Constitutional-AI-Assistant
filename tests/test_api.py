from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_endpoint():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_malformed_chat_input():
    response = TestClient(app).post("/api/chat", json={"message": " "})
    assert response.status_code == 422
    assert "malformed" in response.json()["detail"]

