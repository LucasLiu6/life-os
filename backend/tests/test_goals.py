from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_goal_returns_created_goal() -> None:
    goal_row = {
        "id": "goal-1",
        "domain": "Academics",
        "title": "Finish calculus homework",
        "description": None,
        "why_it_matters": None,
        "target_date": None,
        "status": "active",
        "weekly_target": None,
        "success_metric": None,
        "created_at": "2026-05-29T20:00:00Z",
        "updated_at": "2026-05-29T20:00:00Z",
    }
    mock_supabase = Mock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = (
        SimpleNamespace(data=[goal_row])
    )

    with patch("app.api.goals.get_supabase_client", return_value=mock_supabase):
        response = client.post(
            "/goals",
            json={"domain": "Academics", "title": "Finish calculus homework"},
        )

    assert response.status_code == 201
    assert response.json() == goal_row
    mock_supabase.table.assert_called_once_with("goals")
    mock_supabase.table.return_value.insert.assert_called_once_with(
        {
            "domain": "Academics",
            "title": "Finish calculus homework",
            "description": None,
            "why_it_matters": None,
            "target_date": None,
            "status": "active",
            "weekly_target": None,
            "success_metric": None,
        }
    )


def test_list_goals_returns_goals() -> None:
    goal_rows = [
        {
            "id": "goal-1",
            "domain": "Academics",
            "title": "Finish calculus homework",
            "description": None,
            "why_it_matters": None,
            "target_date": None,
            "status": "active",
            "weekly_target": None,
            "success_metric": None,
            "created_at": "2026-05-29T20:00:00Z",
            "updated_at": "2026-05-29T20:00:00Z",
        }
    ]
    mock_supabase = Mock()
    (
        mock_supabase.table.return_value.select.return_value.order.return_value.execute
    ).return_value = SimpleNamespace(data=goal_rows)

    with patch("app.api.goals.get_supabase_client", return_value=mock_supabase):
        response = client.get("/goals")

    assert response.status_code == 200
    assert response.json() == goal_rows
    mock_supabase.table.assert_called_once_with("goals")
    mock_supabase.table.return_value.select.assert_called_once_with("*")
    mock_supabase.table.return_value.select.return_value.order.assert_called_once_with(
        "created_at", desc=True
    )
