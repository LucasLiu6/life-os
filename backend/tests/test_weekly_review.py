from datetime import date as date_type
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.weekly_review import build_weekly_review_prompt


client = TestClient(app)


def _mock_table_query(rows: list[dict]) -> Mock:
    query = Mock()
    query.select.return_value = query
    query.eq.return_value = query
    query.gte.return_value = query
    query.lte.return_value = query
    query.lt.return_value = query
    query.order.return_value = query
    query.limit.return_value = query
    query.execute.return_value = SimpleNamespace(data=rows)
    return query


def _mock_insert_query(rows: list[dict] | None = None) -> Mock:
    query = Mock()
    query.insert.return_value.execute.return_value = SimpleNamespace(data=rows or [{}])
    return query


def _mock_supabase(
    *,
    goals: list[dict] | None = None,
    due_tasks: list[dict] | None = None,
    created_tasks: list[dict] | None = None,
    checkins: list[dict] | None = None,
    agent_runs: list[dict] | None = None,
) -> tuple[Mock, dict[str, Mock]]:
    queries = {
        "goals": _mock_table_query(goals or []),
        "due_tasks": _mock_table_query(due_tasks or []),
        "created_tasks": _mock_table_query(created_tasks or []),
        "daily_checkins": _mock_table_query(checkins or []),
        "agent_runs_read": _mock_table_query(agent_runs or []),
        "agent_runs_insert": _mock_insert_query(),
    }
    sequence = [
        queries["goals"],
        queries["due_tasks"],
        queries["created_tasks"],
        queries["daily_checkins"],
        queries["agent_runs_read"],
        queries["agent_runs_insert"],
    ]
    supabase = Mock()
    supabase.table.side_effect = sequence
    return supabase, queries


def test_weekly_review_success_uses_provided_dates_and_logs_agent_run() -> None:
    supabase, queries = _mock_supabase(
        goals=[{"id": "goal-1", "title": "Improve GPA", "status": "active"}],
        due_tasks=[{"id": "task-1", "title": "Study calculus"}],
        created_tasks=[{"id": "task-2", "title": "Update resume"}],
        checkins=[{"id": "checkin-1", "date": "2026-05-29"}],
        agent_runs=[{"id": "run-1", "run_type": "morning_briefing"}],
    )
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(
        output_text="Weekly review text"
    )

    with (
        patch("app.services.weekly_review.get_supabase_client", return_value=supabase),
        patch("app.services.weekly_review.get_openai_client", return_value=openai_client),
    ):
        response = client.post(
            "/agent/weekly-review",
            json={"start_date": "2026-05-23", "end_date": "2026-05-29"},
        )

    assert response.status_code == 200
    assert response.json() == {"review": "Weekly review text"}
    openai_client.responses.create.assert_called_once()
    assert openai_client.responses.create.call_args.kwargs["model"] == settings.openai_model
    prompt = openai_client.responses.create.call_args.kwargs["input"]
    assert "2026-05-23 to 2026-05-29" in prompt
    assert "under 800 words" in prompt
    assert "3-5 concrete next-week targets" in prompt
    assert "Do not pretend to access calendar, email, Telegram, Gmail, or external systems." in prompt
    assert "Do not suggest irreversible actions." in prompt
    queries["agent_runs_insert"].insert.assert_called_once()
    agent_run = queries["agent_runs_insert"].insert.call_args.args[0]
    assert agent_run["run_type"] == "weekly_review"
    assert agent_run["status"] == "success"
    assert agent_run["output"] == "Weekly review text"
    assert agent_run["error_message"] is None


def test_weekly_review_defaults_to_last_7_days_including_today() -> None:
    supabase, queries = _mock_supabase()
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="Review")

    with (
        patch("app.services.weekly_review.date") as mock_date,
        patch("app.services.weekly_review.get_supabase_client", return_value=supabase),
        patch("app.services.weekly_review.get_openai_client", return_value=openai_client),
    ):
        mock_date.today.return_value = date_type(2026, 5, 29)
        response = client.post("/agent/weekly-review", json={})

    assert response.status_code == 200
    queries["due_tasks"].gte.assert_called_once_with("due_date", "2026-05-23")
    queries["due_tasks"].lte.assert_called_once_with("due_date", "2026-05-29")
    queries["created_tasks"].gte.assert_called_once_with("created_at", "2026-05-23")
    queries["created_tasks"].lt.assert_called_once_with("created_at", "2026-05-30")


def test_weekly_review_start_after_end_returns_400() -> None:
    response = client.post(
        "/agent/weekly-review",
        json={"start_date": "2026-05-30", "end_date": "2026-05-29"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "start_date must be before or equal to end_date."


def test_weekly_review_reads_expected_supabase_context() -> None:
    supabase, queries = _mock_supabase()
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="Review")

    with (
        patch("app.services.weekly_review.get_supabase_client", return_value=supabase),
        patch("app.services.weekly_review.get_openai_client", return_value=openai_client),
    ):
        response = client.post(
            "/agent/weekly-review",
            json={"start_date": "2026-05-23", "end_date": "2026-05-29"},
        )

    assert response.status_code == 200
    queries["goals"].eq.assert_called_once_with("status", "active")
    queries["due_tasks"].gte.assert_called_once_with("due_date", "2026-05-23")
    queries["due_tasks"].lte.assert_called_once_with("due_date", "2026-05-29")
    queries["created_tasks"].gte.assert_called_once_with("created_at", "2026-05-23")
    queries["created_tasks"].lt.assert_called_once_with("created_at", "2026-05-30")
    queries["daily_checkins"].gte.assert_called_once_with("date", "2026-05-23")
    queries["daily_checkins"].lte.assert_called_once_with("date", "2026-05-29")
    queries["agent_runs_read"].gte.assert_called_once_with("created_at", "2026-05-23")
    queries["agent_runs_read"].lt.assert_called_once_with("created_at", "2026-05-30")
    queries["agent_runs_read"].limit.assert_called_once_with(20)


def test_weekly_review_dedupes_tasks_by_id() -> None:
    supabase, _ = _mock_supabase(
        due_tasks=[
            {"id": "task-1", "title": "Study calculus"},
            {"id": "task-2", "title": "Update resume"},
        ],
        created_tasks=[
            {"id": "task-1", "title": "Study calculus"},
            {"id": "task-3", "title": "Practice soccer"},
        ],
    )
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="Review")

    with (
        patch("app.services.weekly_review.get_supabase_client", return_value=supabase),
        patch("app.services.weekly_review.get_openai_client", return_value=openai_client),
    ):
        response = client.post(
            "/agent/weekly-review",
            json={"start_date": "2026-05-23", "end_date": "2026-05-29"},
        )

    assert response.status_code == 200
    prompt = openai_client.responses.create.call_args.kwargs["input"]
    assert prompt.count('"id": "task-1"') == 1
    assert '"id": "task-2"' in prompt
    assert '"id": "task-3"' in prompt


def test_weekly_review_openai_failure_logs_failed_agent_run() -> None:
    supabase, queries = _mock_supabase()
    openai_client = Mock()
    openai_client.responses.create.side_effect = RuntimeError("OpenAI unavailable")

    with (
        patch("app.services.weekly_review.get_supabase_client", return_value=supabase),
        patch("app.services.weekly_review.get_openai_client", return_value=openai_client),
    ):
        response = client.post(
            "/agent/weekly-review",
            json={"start_date": "2026-05-23", "end_date": "2026-05-29"},
        )

    assert response.status_code == 500
    assert "Failed to generate weekly review" in response.json()["detail"]
    agent_run = queries["agent_runs_insert"].insert.call_args.args[0]
    assert agent_run["run_type"] == "weekly_review"
    assert agent_run["status"] == "failed"
    assert agent_run["output"] == ""
    assert agent_run["error_message"] == "OpenAI unavailable"


def test_weekly_review_still_returns_when_success_logging_fails() -> None:
    supabase, queries = _mock_supabase()
    queries["agent_runs_insert"].insert.return_value.execute.side_effect = RuntimeError(
        "agent_runs insert failed"
    )
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text="Review")

    with (
        patch("app.services.weekly_review.get_supabase_client", return_value=supabase),
        patch("app.services.weekly_review.get_openai_client", return_value=openai_client),
    ):
        response = client.post(
            "/agent/weekly-review",
            json={"start_date": "2026-05-23", "end_date": "2026-05-29"},
        )

    assert response.status_code == 200
    assert response.json() == {"review": "Review"}


def test_weekly_review_prompt_includes_required_guidance() -> None:
    prompt = build_weekly_review_prompt(
        start_date="2026-05-23",
        end_date="2026-05-29",
        goals=[],
        tasks=[],
        checkins=[],
        agent_runs=[],
    )

    assert "under 800 words" in prompt
    assert "honest but supportive" in prompt
    assert "not shaming" in prompt
    assert "patterns from daily check-ins" in prompt
    assert "progress against active goals" in prompt
    assert "3-5 concrete next-week targets" in prompt
    assert "If stored context is limited" in prompt
    assert "Do not pretend to access calendar, email, Telegram, Gmail, or external systems." in prompt
    assert "Do not suggest irreversible actions." in prompt
