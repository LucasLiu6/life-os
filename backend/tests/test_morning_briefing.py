from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.morning_briefing import build_morning_briefing_prompt


client = TestClient(app)


def _mock_table_query(rows: list[dict]) -> Mock:
    query = Mock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = SimpleNamespace(data=rows)
    return query


def _mock_insert_query(rows: list[dict] | None = None) -> Mock:
    query = Mock()
    query.insert.return_value.execute.return_value = SimpleNamespace(data=rows or [{}])
    return query


def _mock_supabase(
    goals: list[dict] | None = None,
    tasks: list[dict] | None = None,
    checkins: list[dict] | None = None,
) -> tuple[Mock, Mock]:
    agent_runs_query = _mock_insert_query()
    tables = {
        "goals": _mock_table_query(goals or []),
        "tasks": _mock_table_query(tasks or []),
        "daily_checkins": _mock_table_query(checkins or []),
        "agent_runs": agent_runs_query,
    }
    supabase = Mock()
    supabase.table.side_effect = lambda table_name: tables[table_name]
    return supabase, agent_runs_query


def test_morning_briefing_success_returns_briefing_and_logs_agent_run() -> None:
    supabase, agent_runs_query = _mock_supabase(
        goals=[{"id": "goal-1", "title": "Improve GPA", "status": "active"}],
        tasks=[{"id": "task-1", "title": "Study calculus", "status": "open"}],
        checkins=[{"id": "checkin-1", "date": "2026-05-29"}],
    )
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(
        output_text="Good morning. Focus on calculus first."
    )

    with (
        patch(
            "app.services.morning_briefing.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.morning_briefing.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/morning-briefing")

    assert response.status_code == 200
    assert response.json() == {
        "briefing": "Good morning. Focus on calculus first.",
    }
    openai_client.responses.create.assert_called_once()
    assert openai_client.responses.create.call_args.kwargs["model"] == settings.openai_model
    assert "Do not claim access to calendar" in openai_client.responses.create.call_args.kwargs["input"]
    assert "Do not suggest irreversible actions" in openai_client.responses.create.call_args.kwargs["input"]
    assert "If stored context is limited" in openai_client.responses.create.call_args.kwargs["input"]
    agent_runs_query.insert.assert_called_once()
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["run_type"] == "morning_briefing"
    assert agent_run["output"] == "Good morning. Focus on calculus first."
    assert agent_run["status"] == "success"
    assert agent_run["error_message"] is None


def test_morning_briefing_reads_expected_supabase_tables() -> None:
    supabase, _ = _mock_supabase()
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="Briefing")

    with (
        patch(
            "app.services.morning_briefing.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.morning_briefing.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/morning-briefing")

    assert response.status_code == 200
    supabase.table.assert_has_calls(
        [
            call("goals"),
            call("tasks"),
            call("daily_checkins"),
            call("agent_runs"),
        ]
    )


def test_morning_briefing_logs_failed_agent_run_when_openai_fails() -> None:
    supabase, agent_runs_query = _mock_supabase()
    openai_client = Mock()
    openai_client.responses.create.side_effect = RuntimeError("OpenAI unavailable")

    with (
        patch(
            "app.services.morning_briefing.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.morning_briefing.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/morning-briefing")

    assert response.status_code == 500
    assert "Failed to generate morning briefing" in response.json()["detail"]
    agent_runs_query.insert.assert_called_once()
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["run_type"] == "morning_briefing"
    assert agent_run["output"] == ""
    assert agent_run["status"] == "failed"
    assert agent_run["error_message"] == "OpenAI unavailable"


def test_morning_briefing_still_returns_when_success_logging_fails() -> None:
    supabase, agent_runs_query = _mock_supabase()
    agent_runs_query.insert.return_value.execute.side_effect = RuntimeError(
        "agent_runs insert failed"
    )
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="Briefing")

    with (
        patch(
            "app.services.morning_briefing.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.morning_briefing.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/morning-briefing")

    assert response.status_code == 200
    assert response.json() == {"briefing": "Briefing"}


def test_morning_briefing_missing_openai_key_returns_500_and_logs_failure() -> None:
    supabase, agent_runs_query = _mock_supabase()

    with (
        patch(
            "app.services.morning_briefing.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.morning_briefing.get_openai_client",
            side_effect=RuntimeError("Missing OpenAI configuration."),
        ),
    ):
        response = client.post("/agent/morning-briefing")

    assert response.status_code == 500
    assert "Missing OpenAI configuration" in response.json()["detail"]
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["status"] == "failed"
    assert agent_run["error_message"] == "Missing OpenAI configuration."


def test_morning_briefing_prompt_includes_required_safety_rules() -> None:
    prompt = build_morning_briefing_prompt(
        today="2026-05-29",
        goals=[],
        tasks=[],
        checkins=[],
    )

    assert "Do not claim access to calendar, email, Telegram, or external systems." in prompt
    assert "Do not suggest irreversible actions." in prompt
    assert (
        "If stored context is limited, say the briefing is based on limited stored context."
        in prompt
    )
    assert "Stored context is limited: True" in prompt
