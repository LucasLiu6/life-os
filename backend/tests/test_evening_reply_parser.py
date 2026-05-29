from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.evening_reply_parser import build_evening_reply_parser_prompt


client = TestClient(app)


def _created_checkin_row(
    *,
    energy_level: int | None = 7,
    date: str = "2026-05-29",
) -> dict:
    return {
        "id": "checkin-1",
        "date": date,
        "planned_top_3": None,
        "completed": "Finished resume update",
        "blockers": "Got blocked on calculus",
        "energy_level": energy_level,
        "mood": None,
        "notes": None,
        "tomorrow_focus": "Finish the calculus homework",
        "created_at": "2026-05-29T20:00:00Z",
    }


def _mock_insert_query(rows: list[dict] | None = None) -> Mock:
    query = Mock()
    query.insert.return_value.execute.return_value = SimpleNamespace(data=rows or [{}])
    return query


def _mock_supabase(created_checkin: dict | None = None) -> tuple[Mock, Mock, Mock]:
    daily_checkins_query = _mock_insert_query([created_checkin or _created_checkin_row()])
    agent_runs_query = _mock_insert_query()
    tables = {
        "daily_checkins": daily_checkins_query,
        "agent_runs": agent_runs_query,
    }
    supabase = Mock()
    supabase.table.side_effect = lambda table_name: tables[table_name]
    return supabase, daily_checkins_query, agent_runs_query


def _mock_openai(output_text: str) -> Mock:
    openai_client = Mock()
    openai_client.responses.create.return_value = SimpleNamespace(output_text=output_text)
    return openai_client


def test_parse_evening_reply_success_returns_full_created_checkin() -> None:
    created_checkin = _created_checkin_row()
    supabase, daily_checkins_query, agent_runs_query = _mock_supabase(created_checkin)
    openai_client = _mock_openai(
        """
        {
          "date": "2026-05-29",
          "planned_top_3": null,
          "completed": "Finished resume update",
          "blockers": "Got blocked on calculus",
          "energy_level": 7,
          "mood": null,
          "notes": null,
          "tomorrow_focus": "Finish the calculus homework"
        }
        """
    )

    with (
        patch(
            "app.services.evening_reply_parser.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_reply_parser.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post(
            "/agent/parse-evening-reply",
            json={
                "reply": (
                    "I finished my resume update, got blocked on calculus, energy was "
                    "7, and tomorrow I want to finish the calculus homework."
                ),
                "date": "2026-05-29",
            },
        )

    assert response.status_code == 200
    assert response.json() == {"parsed_checkin": created_checkin}
    openai_client.responses.create.assert_called_once()
    assert openai_client.responses.create.call_args.kwargs["model"] == settings.openai_model
    prompt = openai_client.responses.create.call_args.kwargs["input"]
    assert "This is extraction only." in prompt
    assert "Return JSON only." in prompt
    assert "Do not give advice." in prompt
    assert "Do not invent facts." in prompt
    daily_checkins_query.insert.assert_called_once_with(
        {
            "date": "2026-05-29",
            "planned_top_3": None,
            "completed": "Finished resume update",
            "blockers": "Got blocked on calculus",
            "energy_level": 7,
            "mood": None,
            "notes": None,
            "tomorrow_focus": "Finish the calculus homework",
        }
    )
    agent_runs_query.insert.assert_called_once()
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["run_type"] == "parse_evening_reply"
    assert agent_run["status"] == "success"
    assert agent_run["error_message"] is None


def test_parse_evening_reply_rejects_empty_reply() -> None:
    response = client.post(
        "/agent/parse-evening-reply",
        json={"reply": "", "date": "2026-05-29"},
    )

    assert response.status_code == 422


def test_parse_evening_reply_uses_today_when_date_is_omitted() -> None:
    created_checkin = _created_checkin_row(date="2026-05-30")
    supabase, daily_checkins_query, _ = _mock_supabase(created_checkin)
    openai_client = _mock_openai(
        """
        {
          "date": "2026-05-29",
          "planned_top_3": null,
          "completed": "Finished resume update",
          "blockers": null,
          "energy_level": null,
          "mood": null,
          "notes": null,
          "tomorrow_focus": null
        }
        """
    )

    with (
        patch("app.services.evening_reply_parser.date") as mock_date,
        patch(
            "app.services.evening_reply_parser.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_reply_parser.get_openai_client",
            return_value=openai_client,
        ),
    ):
        mock_date.today.return_value.isoformat.return_value = "2026-05-30"
        response = client.post(
            "/agent/parse-evening-reply",
            json={"reply": "Finished resume update."},
        )

    assert response.status_code == 200
    inserted_row = daily_checkins_query.insert.call_args.args[0]
    assert inserted_row["date"] == "2026-05-30"


def test_parse_evening_reply_strips_markdown_json_code_fence() -> None:
    created_checkin = _created_checkin_row()
    supabase, _, _ = _mock_supabase(created_checkin)
    openai_client = _mock_openai(
        """```json
{
  "date": "2026-05-29",
  "planned_top_3": null,
  "completed": "Finished resume update",
  "blockers": null,
  "energy_level": 7,
  "mood": null,
  "notes": null,
  "tomorrow_focus": "Finish calculus"
}
```"""
    )

    with (
        patch(
            "app.services.evening_reply_parser.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_reply_parser.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post(
            "/agent/parse-evening-reply",
            json={"reply": "Energy was 7.", "date": "2026-05-29"},
        )

    assert response.status_code == 200
    assert response.json() == {"parsed_checkin": created_checkin}


def test_parse_evening_reply_missing_energy_level_stays_null() -> None:
    created_checkin = _created_checkin_row(energy_level=None)
    supabase, daily_checkins_query, _ = _mock_supabase(created_checkin)
    openai_client = _mock_openai(
        """
        {
          "date": "2026-05-29",
          "planned_top_3": null,
          "completed": "Finished resume update",
          "blockers": null,
          "energy_level": null,
          "mood": null,
          "notes": null,
          "tomorrow_focus": null
        }
        """
    )

    with (
        patch(
            "app.services.evening_reply_parser.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_reply_parser.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post(
            "/agent/parse-evening-reply",
            json={"reply": "Finished resume update.", "date": "2026-05-29"},
        )

    assert response.status_code == 200
    inserted_row = daily_checkins_query.insert.call_args.args[0]
    assert inserted_row["energy_level"] is None


def test_parse_evening_reply_invalid_energy_level_logs_failure() -> None:
    supabase, _, agent_runs_query = _mock_supabase()
    openai_client = _mock_openai(
        """
        {
          "date": "2026-05-29",
          "planned_top_3": null,
          "completed": null,
          "blockers": null,
          "energy_level": 11,
          "mood": null,
          "notes": null,
          "tomorrow_focus": null
        }
        """
    )

    with (
        patch(
            "app.services.evening_reply_parser.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_reply_parser.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post(
            "/agent/parse-evening-reply",
            json={"reply": "Energy was 11.", "date": "2026-05-29"},
        )

    assert response.status_code == 500
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["run_type"] == "parse_evening_reply"
    assert agent_run["status"] == "failed"
    assert agent_run["error_message"] == "Parsed evening reply failed validation."


def test_parse_evening_reply_invalid_json_logs_failure() -> None:
    supabase, _, agent_runs_query = _mock_supabase()
    openai_client = _mock_openai("not json")

    with (
        patch(
            "app.services.evening_reply_parser.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_reply_parser.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post(
            "/agent/parse-evening-reply",
            json={"reply": "Energy was 7.", "date": "2026-05-29"},
        )

    assert response.status_code == 500
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["status"] == "failed"
    assert agent_run["error_message"] == "OpenAI returned invalid JSON."


def test_parse_evening_reply_daily_checkin_insert_failure_logs_failure() -> None:
    supabase, daily_checkins_query, agent_runs_query = _mock_supabase()
    daily_checkins_query.insert.return_value.execute.return_value = SimpleNamespace(data=[])
    openai_client = _mock_openai(
        """
        {
          "date": "2026-05-29",
          "planned_top_3": null,
          "completed": "Finished resume update",
          "blockers": null,
          "energy_level": 7,
          "mood": null,
          "notes": null,
          "tomorrow_focus": null
        }
        """
    )

    with (
        patch(
            "app.services.evening_reply_parser.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_reply_parser.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post(
            "/agent/parse-evening-reply",
            json={"reply": "Energy was 7.", "date": "2026-05-29"},
        )

    assert response.status_code == 500
    agent_run = agent_runs_query.insert.call_args.args[0]
    assert agent_run["status"] == "failed"
    assert agent_run["error_message"] == "Supabase returned no created daily check-in."


def test_parse_evening_reply_still_returns_when_success_logging_fails() -> None:
    created_checkin = _created_checkin_row()
    supabase, _, agent_runs_query = _mock_supabase(created_checkin)
    agent_runs_query.insert.return_value.execute.side_effect = RuntimeError(
        "agent_runs insert failed"
    )
    openai_client = _mock_openai(
        """
        {
          "date": "2026-05-29",
          "planned_top_3": null,
          "completed": "Finished resume update",
          "blockers": "Got blocked on calculus",
          "energy_level": 7,
          "mood": null,
          "notes": null,
          "tomorrow_focus": "Finish the calculus homework"
        }
        """
    )

    with (
        patch(
            "app.services.evening_reply_parser.get_supabase_client",
            return_value=supabase,
        ),
        patch(
            "app.services.evening_reply_parser.get_openai_client",
            return_value=openai_client,
        ),
    ):
        response = client.post(
            "/agent/parse-evening-reply",
            json={"reply": "Energy was 7.", "date": "2026-05-29"},
        )

    assert response.status_code == 200
    assert response.json() == {"parsed_checkin": created_checkin}


def test_evening_reply_parser_prompt_contains_required_instructions() -> None:
    prompt = build_evening_reply_parser_prompt(
        reply="Finished resume update.",
        selected_date="2026-05-29",
    )

    assert "This is extraction only." in prompt
    assert "Return JSON only." in prompt
    assert "Do not give advice." in prompt
    assert "Do not summarize beyond the requested fields." in prompt
    assert "Do not invent facts." in prompt
    assert "Do not make up mood, blockers, completed items, or tomorrow_focus." in prompt
    assert "If energy_level is not mentioned, use null." in prompt
    assert "Use this date exactly: 2026-05-29" in prompt
