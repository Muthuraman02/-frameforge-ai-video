import subprocess
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


def test_demo_generation_end_to_end(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "GENERATION_MODE", "demo")

    with TestClient(app) as client:
        create_res = client.post(
            "/api/videos",
            json={
                "prompt": "A cinematic astronaut walking across a desert",
                "style": "Cinematic",
                "aspect_ratio": "16:9",
                "duration": "8 seconds",
            },
        )
        assert create_res.status_code == 202
        created = create_res.json()
        assert "job_id" in created
        assert created["status"] == "queued"
        job_id = created["job_id"]

        status_res = client.get(f"/api/videos/{job_id}")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert status_data["status"] == "completed"
        assert status_data["progress"] == 100
        assert status_data["video_url"] == f"/videos/{job_id}"
        assert status_data["error"] is None

        video_res = client.get(status_data["video_url"])
        assert video_res.status_code == 200
        assert video_res.headers["content-type"] == "video/mp4"
        assert len(video_res.content) > 1000

        # Test HTTP Range request support for browser video seeking
        range_res = client.get(
            status_data["video_url"],
            headers={"Range": "bytes=0-1023"},
        )
        assert range_res.status_code == 206
        assert range_res.headers["content-range"].startswith("bytes 0-1023/")
        assert len(range_res.content) == 1024

        # Verify MP4 readability with ffprobe
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            tmp.write(video_res.content)
            tmp.flush()
            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration:stream=codec_type",
                    "-of",
                    "default=noprint_wrappers=1",
                    str(Path(tmp.name)),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            assert "codec_type=video" in probe.stdout
