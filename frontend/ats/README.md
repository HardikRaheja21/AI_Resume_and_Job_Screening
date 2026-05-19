# AI Recruiter ATS Frontend

Modern recruiter-facing ATS dashboard for the AI Recruitment Intelligence Platform.

## Setup

```bash
cd frontend/ats
npm install
cp .env.example .env.local
npm run dev
```

## Environment

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_APP_NAME=AI Recruiter ATS
```

## Build

```bash
npm run build
npm run preview
```

## Vercel

Set `VITE_API_BASE_URL` to the deployed FastAPI backend URL. The app uses SPA rewrites through `vercel.json`.

## Demo Data

When the dashboard is empty, a "Seed demo data" button appears to populate candidate and job demo content for presentation testing.
