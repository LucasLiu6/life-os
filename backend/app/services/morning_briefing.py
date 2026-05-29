from __future__ import annotations

import json
import logging
from datetime import date

from app.config import settings
from app.db.client import get_supabase_client
from app.llm.client import get_openai_client


logger = logging.getLogger(__name__)


def generate_morning_briefing() -> str:
    supabase = get_supabase_client()
    today = date.today().isoformat()

    goals = _fetch_active_goals(supabase)
    tasks = _fetch_open_tasks(supabase)
    checkins = _fetch_recent_checkins(supabase)
    input_summary = _build_input_summary(today, goals, tasks, checkins)
    prompt = build_morning_briefing_prompt(today, goals, tasks, checkins)

    try:
        response = get_openai_client().responses.create(
            model=settings.openai_model,
            input=prompt,
        )
        briefing = response.output_text
    except Exception as error:
        error_summary = _summarize_error(error)
        _try_log_agent_run(
            supabase,
            {
                "run_type": "morning_briefing",
                "input_summary": input_summary,
                "output": "",
                "status": "failed",
                "error_message": error_summary,
            },
        )
        raise RuntimeError(f"Failed to generate morning briefing: {error_summary}") from error

    try:
        _log_agent_run(
            supabase,
            {
                "run_type": "morning_briefing",
                "input_summary": input_summary,
                "output": briefing,
                "status": "success",
                "error_message": None,
            },
        )
    except Exception as error:
        logger.exception("Failed to log successful morning briefing run: %s", error)

    return briefing


def build_morning_briefing_prompt(
    today: str,
    goals: list[dict],
    tasks: list[dict],
    checkins: list[dict],
) -> str:
    context_is_limited = not goals and not tasks and not checkins

    return f"""
You are Life OS, a proactive personal Chief of Staff for one user.

Create a concise morning briefing for today.

Tone:
- direct
- supportive
- practical
- accountability-focused
- not too long

Include:
1. short greeting
2. urgent tasks
3. top 3 priorities
4. recommended time blocks
5. one long-term goal action
6. one risk warning
7. concise motivational note

Rules:
- Do not claim access to calendar, email, Telegram, or external systems.
- Do not suggest irreversible actions.
- If stored context is limited, say the briefing is based on limited stored context.

Current date: {today}
Stored context is limited: {context_is_limited}

Active goals:
{_format_json(goals)}

Open tasks:
{_format_json(tasks)}

Recent daily check-ins:
{_format_json(checkins)}
""".strip()


def _fetch_active_goals(supabase) -> list[dict]:
    response = (
        supabase.table("goals")
        .select("*")
        .eq("status", "active")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def _fetch_open_tasks(supabase) -> list[dict]:
    response = (
        supabase.table("tasks")
        .select("*")
        .eq("status", "open")
        .order("due_date", desc=False)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def _fetch_recent_checkins(supabase) -> list[dict]:
    response = (
        supabase.table("daily_checkins")
        .select("*")
        .order("date", desc=True)
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )
    return response.data or []


def _log_agent_run(supabase, row: dict) -> None:
    response = supabase.table("agent_runs").insert(row).execute()

    if not response.data:
        raise RuntimeError("Supabase returned no created agent run.")


def _try_log_agent_run(supabase, row: dict) -> None:
    try:
        _log_agent_run(supabase, row)
    except Exception as error:
        logger.exception("Failed to log failed morning briefing run: %s", error)


def _build_input_summary(
    today: str,
    goals: list[dict],
    tasks: list[dict],
    checkins: list[dict],
) -> str:
    return (
        f"date={today}; active_goals={len(goals)}; "
        f"open_tasks={len(tasks)}; recent_checkins={len(checkins)}"
    )


def _format_json(value: list[dict]) -> str:
    if not value:
        return "[]"

    return json.dumps(value, indent=2, default=str)


def _summarize_error(error: Exception) -> str:
    summary = str(error).strip()
    return summary or error.__class__.__name__
