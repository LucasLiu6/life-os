from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_task_returns_created_task() -> None:
    task_row = {
        "id": "task-1",
        "domain": "2027 Summer Internship",
        "title": "Update resume",
        "description": None,
        "due_date": None,
        "priority": "medium",
        "status": "open",
        "estimated_minutes": None,
        "source": None,
        "related_goal_id": None,
        "created_at": "2026-05-29T20:00:00Z",
        "updated_at": "2026-05-29T20:00:00Z",
    }
    mock_supabase = Mock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = (
        SimpleNamespace(data=[task_row])
    )

    with patch("app.api.tasks.get_supabase_client", return_value=mock_supabase):
        response = client.post(
            "/tasks",
            json={"domain": "2027 Summer Internship", "title": "Update resume"},
        )

    assert response.status_code == 201
    assert response.json() == task_row
    mock_supabase.table.assert_called_once_with("tasks")
    mock_supabase.table.return_value.insert.assert_called_once_with(
        {
            "domain": "2027 Summer Internship",
            "title": "Update resume",
            "description": None,
            "due_date": None,
            "priority": "medium",
            "status": "open",
            "estimated_minutes": None,
            "source": None,
            "related_goal_id": None,
        }
    )


def test_list_tasks_returns_tasks() -> None:
    task_rows = [
        {
            "id": "task-1",
            "domain": "2027 Summer Internship",
            "title": "Update resume",
            "description": None,
            "due_date": None,
            "priority": "medium",
            "status": "open",
            "estimated_minutes": None,
            "source": None,
            "related_goal_id": None,
            "created_at": "2026-05-29T20:00:00Z",
            "updated_at": "2026-05-29T20:00:00Z",
        }
    ]
    mock_supabase = Mock()
    (
        mock_supabase.table.return_value.select.return_value.order.return_value.execute
    ).return_value = SimpleNamespace(data=task_rows)

    with patch("app.api.tasks.get_supabase_client", return_value=mock_supabase):
        response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == task_rows
    mock_supabase.table.assert_called_once_with("tasks")
    mock_supabase.table.return_value.select.assert_called_once_with("*")
    mock_supabase.table.return_value.select.return_value.order.assert_called_once_with(
        "created_at", desc=True
    )
