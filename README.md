# FrameForge AI Video Studio

Full-stack AI Video Studio with a Next.js 14 frontend and a modular FastAPI + FFmpeg backend.

## Project Structure

- `app/` — Next.js 14 App Router frontend (`app/page.tsx` with job polling, progress bar, MP4 preview, and download)
- `backend/` — FastAPI backend (`app/`, `tests/`, `Dockerfile`, `render.yaml`, `requirements.txt`)

## Run Locally

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 2. Frontend
```bash
npm install
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local
npm run dev
```
Open `http://localhost:3000`.

## Run Backend Tests
```bash
cd backend
pytest -q
```

## Deploy
1. **Backend (Render)**: Deploy `backend/` as a Docker Web Service using `backend/Dockerfile` (or `backend/render.yaml`).
2. **Frontend (Vercel)**: Set `NEXT_PUBLIC_API_BASE_URL` to your deployed Render backend URL and redeploy.

Never commit `.env`, `.env.local`, or API keys.
