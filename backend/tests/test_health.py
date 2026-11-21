from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "FrameForge AI Video Backend"
    assert data["version"] == "1.0.0"


def test_cors_allows_production_frontend_origin():
    origin = "https://frameforge-ai-video-three.vercel.app"
    response = client.options(
        "/api/videos",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == origin
