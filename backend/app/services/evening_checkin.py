from __future__ import annotations

import json
import logging
from datetime import date

from app.config import settings
from app.db.client import get_supabase_client
from app.llm.client import get_openai_client


logger = logging.getLogger(__name__)


def generate_evening_checkin() -> str:
    supabase = get_supabase_client()
    today = date.today().isoformat()

    goals = _fetch_active_goals(supabase)
    tasks = _fetch_open_tasks(supabase)
    morning_briefings = _fetch_recent_morning_briefings(supabase)
    checkins = _fetch_recent_checkins(supabase)
    input_summary = _build_input_summary(today, goals, tasks, morning_briefings, checkins)
    prompt = build_evening_checkin_prompt(
        today,
        goals,
        tasks,
        morning_briefings,
        checkins,
    )

    try:
        response = get_openai_client().responses.create(
            model=settings.openai_model,
            input=prompt,
        )
        message = response.output_text
    except Exception as error:
        error_summary = _summarize_error(error)
        _try_log_agent_run(
            supabase,
            {
                "run_type": "evening_checkin",
                "input_summary": input_summary,
                "output": "",
                "status": "failed",
                "error_message": error_summary,
            },
        )
        raise RuntimeError(f"Failed to generate evening check-in: {error_summary}") from error

    try:
        _log_agent_run(
            supabase,
            {
                "run_type": "evening_checkin",
                "input_summary": input_summary,
                "output": message,
                "status": "success",
                "error_message": None,
            },
        )
    except Exception as error:
        logger.exception("Failed to log successful evening check-in run: %s", error)

    return message


def build_evening_checkin_prompt(
    today: str,
    goals: list[dict],
    tasks: list[dict],
    morning_briefings: list[dict],
    checkins: list[dict],
) -> str:
    context_is_limited = not goals and not tasks and not morning_briefings and not checkins
    morning_context_note = (
        "Recent morning briefing context is available."
        if morning_briefings
        else (
            "No recent morning briefing is available. Still generate a useful check-in "
            "based on active goals, open tasks, and recent daily check-ins."
        )
    )

    return f"""
You are Life OS, a proactive personal Chief of Staff for one user.

Create a short evening check-in message for today.

Tone:
- practical
- supportive
- direct
- accountability-focused
- not shaming

Requirements:
- Keep it concise: 5-7 short questions maximum, ideally 120-180 words or less.
- Reference today's likely priorities from open tasks and the latest morning briefing if available.
- If no recent morning briefing is available, still generate a useful check-in from active goals, open tasks, and recent daily check-ins.
- Ask whether today's top priorities were completed.
- Ask what was completed.
- Ask what got blocked.
- Ask for energy_level from 1 to 10.
- Ask for tomorrow_focus.

Safety rules:
- Do not shame the user.
- Do not pretend to access calendar, email, Telegram, or external systems.
- Do not suggest irreversible actions.

Current date: {today}
Stored context is limited: {context_is_limited}
Morning briefing context: {morning_context_note}

Active goals:
{_format_json(goals)}

Open tasks:
{_format_json(tasks)}

Recent morning briefings:
{_format_json(morning_briefings)}

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


def _fetch_recent_morning_briefings(supabase) -> list[dict]:
    response = (
        supabase.table("agent_runs")
        .select("*")
        .eq("run_type", "morning_briefing")
        .order("created_at", desc=True)
        .limit(3)
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
        logger.exception("Failed to log failed evening check-in run: %s", error)


def _build_input_summary(
    today: str,
    goals: list[dict],
    tasks: list[dict],
    morning_briefings: list[dict],
    checkins: list[dict],
) -> str:
    return (
        f"date={today}; active_goals={len(goals)}; open_tasks={len(tasks)}; "
        f"recent_morning_briefings={len(morning_briefings)}; "
        f"recent_checkins={len(checkins)}"
    )


def _format_json(value: list[dict]) -> str:
    if not value:
        return "[]"

    return json.dumps(value, indent=2, default=str)


def _summarize_error(error: Exception) -> str:
    summary = str(error).strip()
    return summary or error.__class__.__name__
