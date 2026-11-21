# FrameForge AI Video Studio

Mobile-first Next.js frontend.

## Run locally
```bash
npm install
npm run dev
```

## Deploy
Import this repository into Vercel. Framework: Next.js; root directory: ./.

## Backend
Set NEXT_PUBLIC_API_BASE_URL in Vercel to the deployed FastAPI backend URL. The UI sends POST /api/videos with prompt, style, aspect_ratio, and duration. This repository currently contains the frontend only; actual video generation requires a separately deployed backend and provider credentials. Never commit API keys or .env files.
