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

Then edit `.env` and set your local Supabase values:

```text
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

Do not commit `.env` or real Supabase keys.

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

## Goals And Tasks API

After starting the server, list goals:

```bash
curl http://127.0.0.1:8000/goals
```

Create a goal:

```bash
curl -X POST http://127.0.0.1:8000/goals \
  -H "Content-Type: application/json" \
  -d '{"domain":"Academics","title":"Finish calculus homework"}'
```

List tasks:

```bash
curl http://127.0.0.1:8000/tasks
```

Create a task:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"domain":"2027 Summer Internship","title":"Update resume"}'
```
