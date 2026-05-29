from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.evening_checkin import build_evening_checkin_prompt


client = TestClient(app)


def _mock_table_query(rows: list[dict]) -> Mock:
    query = Mock()
    query.select.return_value = query
    query.eq.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = SimpleNamespace(data=rows)
    return query


def _mock_agent_runs_query(
    morning_runs: list[dict] | None = None,
    insert_rows: list[dict] | None = None,
) -> Mock:
    query = _mock_table_query(morning_runs or [])
    query.insert.return_value.execute.return_value = SimpleNamespace(
        data=insert_rows or [{}]
    )
    return query


def _mock_supabase(
    goals: list[dict] | None = None,
    tasks: list[dict] | None = None,
    morning_runs: list[dict] | None = None,
    checkins: list[dict] | None = None,
) -> tuple[Mock, Mock]:
    agent_runs_query = _mock_agent_runs_query(morning_runs)
    tables = {
        "goals": _mock_table_query(goals or []),
        "tasks": _mock_table_query(tasks or []),
        "agent_runs": agent_runs_query,
        "daily_checkins": _mock_table_query(checkins or []),
    }
    supabase = Mock()
    supabase.table.side_effect = lambda table_name: tables[table_name]
    return supabase, agent_runs_query


def test_evening_checkin_success_returns_message_and_logs_agent_run() -> None:
    supabase, agent_runs_query = _mock_supabase(
        goals=[{"id": "goal-1", "title": "Improve GPA", "status": "active"}],
        tasks=[{"id": "task-1", "title": "Study calculus", "status": "open"}],
        morning_runs=[
            {
                "id": "run-1",
                "run_type": "morning_briefing",
                "output": "Focus on calculus first.",
            }
        ],
        checkins=[{"id": "checkin-1", "date": "2026-05-29"}],
    )
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(
        output_text="Quick check-in: did you finish calculus?"
    )

    with (
        patch(
            "app.services.evening_checkin.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_checkin.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/evening-checkin")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Quick check-in: did you finish calculus?",
    }
    openai_client.responses.create.assert_called_once()
    assert openai_client.responses.create.call_args.kwargs["model"] == settings.openai_model
    prompt = openai_client.responses.create.call_args.kwargs["input"]
    assert "Keep it concise: 5-7 short questions maximum" in prompt
    assert "Do not shame the user." in prompt
    assert "Do not pretend to access calendar, email, Telegram, or external systems." in prompt
    assert "Do not suggest irreversible actions." in prompt
    assert "Ask for energy_level from 1 to 10." in prompt
    assert "Ask for tomorrow_focus." in prompt
    agent_runs_query.insert.assert_called_once()
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["run_type"] == "evening_checkin"
    assert agent_run["output"] == "Quick check-in: did you finish calculus?"
    assert agent_run["status"] == "success"
    assert agent_run["error_message"] is None


def test_evening_checkin_reads_expected_supabase_tables() -> None:
    supabase, agent_runs_query = _mock_supabase()
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="Check-in")

    with (
        patch(
            "app.services.evening_checkin.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_checkin.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/evening-checkin")

    assert response.status_code == 200
    supabase.table.assert_has_calls(
        [
            call("goals"),
            call("tasks"),
            call("agent_runs"),
            call("daily_checkins"),
            call("agent_runs"),
        ]
    )
    agent_runs_query.eq.assert_any_call("run_type", "morning_briefing")
    agent_runs_query.limit.assert_called_once_with(3)


def test_evening_checkin_works_without_recent_morning_briefings() -> None:
    supabase, _ = _mock_supabase(morning_runs=[])
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(
        output_text="No morning brief found, but let's check in."
    )

    with (
        patch(
            "app.services.evening_checkin.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_checkin.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/evening-checkin")

    assert response.status_code == 200
    assert response.json() == {
        "message": "No morning brief found, but let's check in.",
    }
    prompt = openai_client.responses.create.call_args.kwargs["input"]
    assert "No recent morning briefing is available." in prompt


def test_evening_checkin_logs_failed_agent_run_when_openai_fails() -> None:
    supabase, agent_runs_query = _mock_supabase()
    openai_client = Mock()
    openai_client.responses.create.side_effect = RuntimeError("OpenAI unavailable")

    with (
        patch(
            "app.services.evening_checkin.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_checkin.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/evening-checkin")

    assert response.status_code == 500
    assert "Failed to generate evening check-in" in response.json()["detail"]
    agent_runs_query.insert.assert_called_once()
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["run_type"] == "evening_checkin"
    assert agent_run["output"] == ""
    assert agent_run["status"] == "failed"
    assert agent_run["error_message"] == "OpenAI unavailable"


def test_evening_checkin_still_returns_when_success_logging_fails() -> None:
    supabase, agent_runs_query = _mock_supabase()
    agent_runs_query.insert.return_value.execute.side_effect = RuntimeError(
        "agent_runs insert failed"
    )
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="Check-in")

    with (
        patch(
            "app.services.evening_checkin.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_checkin.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post("/agent/evening-checkin")

    assert response.status_code == 200
    assert response.json() == {"message": "Check-in"}


def test_evening_checkin_prompt_includes_required_rules() -> None:
    prompt = build_evening_checkin_prompt(
        today="2026-05-29",
        goals=[],
        tasks=[],
        morning_briefings=[],
        checkins=[],
    )

    assert "Keep it concise: 5-7 short questions maximum" in prompt
    assert "ideally 120-180 words or less" in prompt
    assert "No recent morning briefing is available." in prompt
    assert "Do not shame the user." in prompt
    assert "Do not pretend to access calendar, email, Telegram, or external systems." in prompt
    assert "Do not suggest irreversible actions." in prompt
    assert "Ask for energy_level from 1 to 10." in prompt
    assert "Ask for tomorrow_focus." in prompt
