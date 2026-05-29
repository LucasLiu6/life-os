from __future__ import annotations

import json
import logging
from datetime import date, timedelta

from app.config import settings
from app.db.client import get_supabase_client
from app.llm.client import get_openai_client


logger = logging.getLogger(__name__)


class InvalidWeeklyReviewWindow(ValueError):
    pass


def generate_weekly_review(
    start_date: date | None = None,
    end_date: date | None = None,
) -> str:
    resolved_start, resolved_end = _resolve_review_window(start_date, end_date)
    next_day = (resolved_end + timedelta(days=1)).isoformat()
    start = resolved_start.isoformat()
    end = resolved_end.isoformat()
    input_summary = _build_input_summary(start, end, [], [], [], [])

    supabase = get_supabase_client()

    try:
        goals = _fetch_active_goals(supabase)
        tasks = _fetch_tasks_in_window(supabase, start, end, next_day)
        checkins = _fetch_daily_checkins(supabase, start, end)
        agent_runs = _fetch_agent_runs(supabase, start, next_day)
        input_summary = _build_input_summary(start, end, goals, tasks, checkins, agent_runs)
        prompt = build_weekly_review_prompt(start, end, goals, tasks, checkins, agent_runs)

        response = get_openai_client().responses.create(
            model=settings.openai_model,
            input=prompt,
        )
        review = response.output_text
    except Exception as error:
        error_summary = _summarize_error(error)
        _try_log_agent_run(
            supabase,
            {
                "run_type": "weekly_review",
                "input_summary": input_summary,
                "output": "",
                "status": "failed",
                "error_message": error_summary,
            },
        )
        raise RuntimeError(f"Failed to generate weekly review: {error_summary}") from error

    try:
        _log_agent_run(
            supabase,
            {
                "run_type": "weekly_review",
                "input_summary": input_summary,
                "output": review,
                "status": "success",
                "error_message": None,
            },
        )
    except Exception as error:
        logger.exception("Failed to log successful weekly review run: %s", error)

    return review


def build_weekly_review_prompt(
    start_date: str,
    end_date: str,
    goals: list[dict],
    tasks: list[dict],
    checkins: list[dict],
    agent_runs: list[dict],
) -> str:
    context_is_limited = not goals and not tasks and not checkins and not agent_runs

    return f"""
You are Life OS, a proactive personal Chief of Staff for one user.

Create a structured but concise weekly review, ideally under 800 words.

Review window:
{start_date} to {end_date}

Tone:
- honest but supportive
- direct
- practical
- accountability-focused
- not shaming

Include:
1. what went well
2. where the user fell behind
3. patterns from daily check-ins
4. progress against active goals where possible
5. suggested focus areas
6. 3-5 concrete next-week targets
7. concise advice

Rules:
- If stored context is limited, say the review is based on limited stored context and still give useful next-week targets.
- Do not pretend to access calendar, email, Telegram, Gmail, or external systems.
- Do not suggest irreversible actions.

Stored context is limited: {context_is_limited}

Active goals:
{_format_json(goals)}

Tasks in review window:
{_format_json(tasks)}

Daily check-ins in review window:
{_format_json(checkins)}

Relevant agent runs:
{_format_json(agent_runs)}
""".strip()


def _resolve_review_window(
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date]:
    if start_date is None and end_date is None:
        resolved_end = date.today()
        resolved_start = resolved_end - timedelta(days=6)
    elif start_date is None:
        resolved_end = end_date
        resolved_start = resolved_end - timedelta(days=6)
    elif end_date is None:
        resolved_start = start_date
        resolved_end = date.today()
    else:
        resolved_start = start_date
        resolved_end = end_date

    if resolved_start > resolved_end:
        raise InvalidWeeklyReviewWindow("start_date must be before or equal to end_date.")

    return resolved_start, resolved_end


def _fetch_active_goals(supabase) -> list[dict]:
    response = (
        supabase.table("goals")
        .select("*")
        .eq("status", "active")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def _fetch_tasks_in_window(
    supabase,
    start_date: str,
    end_date: str,
    next_day: str,
) -> list[dict]:
    due_tasks = _fetch_tasks_due_in_window(supabase, start_date, end_date)
    created_tasks = _fetch_tasks_created_in_window(supabase, start_date, next_day)
    return _dedupe_tasks_by_id([*due_tasks, *created_tasks])


def _fetch_tasks_due_in_window(
    supabase,
    start_date: str,
    end_date: str,
) -> list[dict]:
    response = (
        supabase.table("tasks")
        .select("*")
        .gte("due_date", start_date)
        .lte("due_date", end_date)
        .order("due_date", desc=False)
        .execute()
    )
    return response.data or []


def _fetch_tasks_created_in_window(
    supabase,
    start_date: str,
    next_day: str,
) -> list[dict]:
    response = (
        supabase.table("tasks")
        .select("*")
        .gte("created_at", start_date)
        .lt("created_at", next_day)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def _dedupe_tasks_by_id(tasks: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen_ids: set[str] = set()

    for task in tasks:
        task_id = task.get("id")
        if task_id is None:
            deduped.append(task)
            continue
        if task_id in seen_ids:
            continue
        seen_ids.add(task_id)
        deduped.append(task)

    return deduped


def _fetch_daily_checkins(
    supabase,
    start_date: str,
    end_date: str,
) -> list[dict]:
    response = (
        supabase.table("daily_checkins")
        .select("*")
        .gte("date", start_date)
        .lte("date", end_date)
        .order("date", desc=True)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def _fetch_agent_runs(
    supabase,
    start_date: str,
    next_day: str,
) -> list[dict]:
    response = (
        supabase.table("agent_runs")
        .select("*")
        .gte("created_at", start_date)
        .lt("created_at", next_day)
        .order("created_at", desc=True)
        .limit(20)
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
        logger.exception("Failed to log failed weekly review run: %s", error)


def _build_input_summary(
    start_date: str,
    end_date: str,
    goals: list[dict],
    tasks: list[dict],
    checkins: list[dict],
    agent_runs: list[dict],
) -> str:
    return (
        f"start_date={start_date}; end_date={end_date}; "
        f"active_goals={len(goals)}; tasks={len(tasks)}; "
        f"daily_checkins={len(checkins)}; agent_runs={len(agent_runs)}"
    )


def _format_json(value: list[dict]) -> str:
    if not value:
        return "[]"

    return json.dumps(value, indent=2, default=str)


def _summarize_error(error: Exception) -> str:
    summary = str(error).strip()
    return summary or error.__class__.__name__
