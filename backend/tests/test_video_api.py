from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

client = TestClient(app)


def test_missing_job_returns_404():
    response = client.get("/api/videos/ff_nonexistent_1234")
    assert response.status_code == 404


def test_missing_video_file_returns_404():
    response = client.get("/videos/ff_nonexistent_1234")
    assert response.status_code == 404


def test_failed_job_returns_safe_error(monkeypatch):
    # Force AI mode with no credentials so job fails safely
    settings = get_settings()
    monkeypatch.setattr(settings, "GENERATION_MODE", "ai")
    monkeypatch.setattr(settings, "AI_PROVIDER", "none")
    monkeypatch.setattr(settings, "AI_API_KEY", "super-secret-do-not-leak")

    with TestClient(app) as local_client:
        create_res = local_client.post(
            "/api/videos",
            json={
                "prompt": "Test failure handling",
                "style": "Cinematic",
                "aspect_ratio": "16:9",
                "duration": "8 seconds",
            },
        )
        assert create_res.status_code == 202
        job_id = create_res.json()["job_id"]

        status_res = local_client.get(f"/api/videos/{job_id}")
        assert status_res.status_code == 200
        body = status_res.json()
        assert body["status"] == "failed"
        assert body["error"] is not None
        assert "super-secret-do-not-leak" not in body["error"]
        assert "Traceback" not in body["error"]
