# Life OS Backend

Initial FastAPI backend skeleton for Life OS.

This version only includes:

- Clean FastAPI project structure
- `GET /health`
- Environment variable setup
- Placeholder modules for future database, agent, scheduler, and Telegram work
- Minimal health endpoint test

It does not connect to Supabase, Telegram, OpenAI, LangGraph, APScheduler, Gmail, Calendar, voice, dashboard, or computer use yet.

## Local Setup

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run Locally

From `backend/` with the virtual environment active:

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "life-os-backend",
  "environment": "local"
}
```

## Run Tests

From `backend/` with the virtual environment active:

```bash
pytest
```
