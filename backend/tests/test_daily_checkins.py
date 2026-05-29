from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def daily_checkin_row() -> dict:
    return {
        "id": "checkin-1",
        "date": "2026-05-29",
        "planned_top_3": "Study calculus, update resume, soccer training",
        "completed": "Updated resume",
        "blockers": "Calculus took longer than expected",
        "energy_level": 7,
        "mood": "focused",
        "notes": "Need to start earlier tomorrow",
        "tomorrow_focus": "Finish calculus homework",
        "created_at": "2026-05-29T20:00:00Z",
    }


def test_create_daily_checkin_returns_created_checkin() -> None:
    checkin = daily_checkin_row()
    mock_supabase = Mock()
    mock_supabase.table.return_value.insert.return_value.execute.return_value = (
        SimpleNamespace(data=[checkin])
    )

    with patch("app.api.daily_checkins.get_supabase_client", return_value=mock_supabase):
        response = client.post(
            "/daily-checkins",
            json={
                "date": "2026-05-29",
                "planned_top_3": "Study calculus, update resume, soccer training",
                "completed": "Updated resume",
                "blockers": "Calculus took longer than expected",
                "energy_level": 7,
                "mood": "focused",
                "notes": "Need to start earlier tomorrow",
                "tomorrow_focus": "Finish calculus homework",
            },
        )

    assert response.status_code == 201
    assert response.json() == checkin
    mock_supabase.table.assert_called_once_with("daily_checkins")
    mock_supabase.table.return_value.insert.assert_called_once_with(
        {
            "date": "2026-05-29",
            "planned_top_3": "Study calculus, update resume, soccer training",
            "completed": "Updated resume",
            "blockers": "Calculus took longer than expected",
            "energy_level": 7,
            "mood": "focused",
            "notes": "Need to start earlier tomorrow",
            "tomorrow_focus": "Finish calculus homework",
        }
    )


def test_create_daily_checkin_rejects_energy_level_below_one() -> None:
    response = client.post(
        "/daily-checkins",
        json={"date": "2026-05-29", "energy_level": 0},
    )

    assert response.status_code == 422


def test_create_daily_checkin_rejects_energy_level_above_ten() -> None:
    response = client.post(
        "/daily-checkins",
        json={"date": "2026-05-29", "energy_level": 11},
    )

    assert response.status_code == 422


def test_list_daily_checkins_defaults_to_limit_30() -> None:
    checkins = [daily_checkin_row()]
    mock_query = Mock()
    mock_query.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = SimpleNamespace(data=checkins)
    mock_supabase = Mock()
    mock_supabase.table.return_value = mock_query

    with patch("app.api.daily_checkins.get_supabase_client", return_value=mock_supabase):
        response = client.get("/daily-checkins")

    assert response.status_code == 200
    assert response.json() == checkins
    mock_supabase.table.assert_called_once_with("daily_checkins")
    mock_query.select.assert_called_once_with("*")
    mock_query.order.assert_has_calls(
        [call("date", desc=True), call("created_at", desc=True)]
    )
    mock_query.limit.assert_called_once_with(30)
    mock_query.execute.assert_called_once_with()


def test_list_daily_checkins_applies_filters_and_limit() -> None:
    checkins = [daily_checkin_row()]
    mock_query = Mock()
    mock_query.select.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.lte.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.execute.return_value = SimpleNamespace(data=checkins)
    mock_supabase = Mock()
    mock_supabase.table.return_value = mock_query

    with patch("app.api.daily_checkins.get_supabase_client", return_value=mock_supabase):
        response = client.get(
            "/daily-checkins?limit=7&start_date=2026-05-01&end_date=2026-05-29"
        )

    assert response.status_code == 200
    assert response.json() == checkins
    mock_query.order.assert_has_calls(
        [call("date", desc=True), call("created_at", desc=True)]
    )
    mock_query.gte.assert_called_once_with("date", "2026-05-01")
    mock_query.lte.assert_called_once_with("date", "2026-05-29")
    mock_query.limit.assert_called_once_with(7)
    mock_query.execute.assert_called_once_with()
