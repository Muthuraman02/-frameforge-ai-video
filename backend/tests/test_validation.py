from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_empty_prompt_rejected():
    response = client.post(
        "/api/videos",
        json={
            "prompt": "   ",
            "style": "Cinematic",
            "aspect_ratio": "16:9",
            "duration": "8 seconds",
        },
    )
    assert response.status_code == 422


def test_invalid_style_rejected():
    response = client.post(
        "/api/videos",
        json={
            "prompt": "An astronaut on Mars",
            "style": "Watercolor",
            "aspect_ratio": "16:9",
            "duration": "8 seconds",
        },
    )
    assert response.status_code == 422


def test_invalid_aspect_ratio_rejected():
    response = client.post(
        "/api/videos",
        json={
            "prompt": "An astronaut on Mars",
            "style": "Cinematic",
            "aspect_ratio": "4:3",
            "duration": "8 seconds",
        },
    )
    assert response.status_code == 422


def test_invalid_duration_rejected():
    response = client.post(
        "/api/videos",
        json={
            "prompt": "An astronaut on Mars",
            "style": "Cinematic",
            "aspect_ratio": "16:9",
            "duration": "45 seconds",
        },
    )
    assert response.status_code == 422
