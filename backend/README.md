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
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.2
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

## Daily Check-ins API

List recent daily check-ins:

```bash
curl http://127.0.0.1:8000/daily-checkins
```

List the last 7 daily check-ins:

```bash
curl "http://127.0.0.1:8000/daily-checkins?limit=7"
```

List daily check-ins in a date range:

```bash
curl "http://127.0.0.1:8000/daily-checkins?start_date=2026-05-01&end_date=2026-05-29"
```

Create a daily check-in:

```bash
curl -X POST http://127.0.0.1:8000/daily-checkins \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2026-05-29",
    "planned_top_3": "Study calculus, update resume, soccer training",
    "completed": "Updated resume",
    "blockers": "Calculus took longer than expected",
    "energy_level": 7,
    "mood": "focused",
    "notes": "Need to start earlier tomorrow",
    "tomorrow_focus": "Finish calculus homework"
  }'
```

## Morning Briefing API

Generate a morning briefing from active goals, open tasks, and recent daily check-ins:

```bash
curl -X POST http://127.0.0.1:8000/agent/morning-briefing
```

Expected response shape:

```json
{
  "briefing": "Good morning..."
}
```
