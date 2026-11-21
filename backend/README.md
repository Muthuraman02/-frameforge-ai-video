# FrameForge AI Video Backend

Modular FastAPI backend for **FrameForge AI Video Studio** supporting:
- **Demo Mode (`GENERATION_MODE=demo`)**: Free-first deterministic video rendering using Pillow + FFmpeg (with optional Edge TTS narration). Clearly labeled `DEMO MODE`.
- **Real AI Mode (`GENERATION_MODE=ai`)**: Pluggable provider interfaces (`ScriptProvider`, `ImageProvider`, `VideoProvider`, `TTSProvider`) ready for real AI video APIs without rewriting the backend.

## Local Setup

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health check: `http://localhost:8000/health`
- Swagger docs: `http://localhost:8000/docs`

## Run Tests

```bash
cd backend
pytest -q
```

## Render Deployment

1. Connect your GitHub repository to Render.
2. Deploy as a **Docker Web Service** with Root Directory set to `backend` (or use `backend/render.yaml`).
3. Set `FRONTEND_ORIGINS` to include `https://frameforge-ai-video-three.vercel.app`.
4. Verify `GET https://YOUR-BACKEND-URL/health`.

### Render Free Tier Limitations
- **Sleep behavior**: Free web services spin down after 15 minutes of inactivity; the first request after sleep takes ~30–60 seconds.
- **CPU/RAM**: Free instances have limited CPU and 512 MB RAM; `MAX_CONCURRENT_JOBS=1` is enforced to prevent out-of-memory errors during FFmpeg encoding.
- **Ephemeral filesystem**: Local SQLite databases and files in `storage/videos/` are wiped on redeploys or restarts. For persistent production storage, attach a Render Persistent Disk (paid) or implement an S3/Cloudflare R2 adapter in `app/services/storage_service.py` and use managed PostgreSQL via `DATABASE_URL`.
