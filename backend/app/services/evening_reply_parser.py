from __future__ import annotations

import json
import logging
from datetime import date
from json import JSONDecodeError

from pydantic import ValidationError

from app.config import settings
from app.db.client import get_supabase_client
from app.llm.client import get_openai_client
from app.schemas.daily_checkins import DailyCheckinCreate


logger = logging.getLogger(__name__)


def parse_evening_reply(reply: str, checkin_date: date | None = None) -> dict:
    supabase = get_supabase_client()
    selected_date = (checkin_date or date.today()).isoformat()
    input_summary = _build_input_summary(selected_date, reply)
    prompt = build_evening_reply_parser_prompt(reply, selected_date)

    try:
        response = get_openai_client().responses.create(
            model=settings.openai_model,
            input=prompt,
        )
        parsed_payload = _parse_model_json(response.output_text)
        parsed_payload["date"] = selected_date
        validated_checkin = DailyCheckinCreate.model_validate(parsed_payload)
        created_checkin = _insert_daily_checkin(
            supabase,
            validated_checkin.model_dump(mode="json"),
        )
    except Exception as error:
        error_summary = _summarize_error(error)
        _try_log_agent_run(
            supabase,
            {
                "run_type": "parse_evening_reply",
                "input_summary": input_summary,
                "output": "",
                "status": "failed",
                "error_message": error_summary,
            },
        )
        raise RuntimeError(f"Failed to parse evening reply: {error_summary}") from error

    try:
        _log_agent_run(
            supabase,
            {
                "run_type": "parse_evening_reply",
                "input_summary": input_summary,
                "output": json.dumps(created_checkin, default=str),
                "status": "success",
                "error_message": None,
            },
        )
    except Exception as error:
        logger.exception("Failed to log successful evening reply parser run: %s", error)

    return created_checkin


def build_evening_reply_parser_prompt(reply: str, selected_date: str) -> str:
    return f"""
You extract a user's evening check-in reply into JSON.

This is extraction only.
Return JSON only. Do not use markdown.
Do not give advice.
Do not summarize beyond the requested fields.
Do not invent facts.
If a field is not mentioned, use null or an empty string.
Do not make up mood, blockers, completed items, or tomorrow_focus.
If energy_level is not mentioned, use null.
If energy_level is present, it must be an integer from 1 to 10.
Use this date exactly: {selected_date}

Return exactly these keys:
{{
  "date": "{selected_date}",
  "planned_top_3": null,
  "completed": null,
  "blockers": null,
  "energy_level": null,
  "mood": null,
  "notes": null,
  "tomorrow_focus": null
}}

User reply:
{reply}
""".strip()


def _parse_model_json(output_text: str) -> dict:
    cleaned_text = _strip_markdown_json_wrapper(output_text)

    try:
        parsed = json.loads(cleaned_text)
    except JSONDecodeError as error:
        raise ValueError("OpenAI returned invalid JSON.") from error

    if not isinstance(parsed, dict):
        raise ValueError("OpenAI returned JSON that was not an object.")

    return parsed


def _strip_markdown_json_wrapper(output_text: str) -> str:
    text = output_text.strip()

    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _insert_daily_checkin(supabase, row: dict) -> dict:
    response = supabase.table("daily_checkins").insert(row).execute()

    if not response.data:
        raise RuntimeError("Supabase returned no created daily check-in.")

    return response.data[0]


def _log_agent_run(supabase, row: dict) -> None:
    response = supabase.table("agent_runs").insert(row).execute()

    if not response.data:
        raise RuntimeError("Supabase returned no created agent run.")


def _try_log_agent_run(supabase, row: dict) -> None:
    try:
        _log_agent_run(supabase, row)
    except Exception as error:
        logger.exception("Failed to log failed evening reply parser run: %s", error)


def _build_input_summary(selected_date: str, reply: str) -> str:
    return f"date={selected_date}; reply_length={len(reply)}"


def _summarize_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        return "Parsed evening reply failed validation."

    summary = str(error).strip()
    return summary or error.__class__.__name__
