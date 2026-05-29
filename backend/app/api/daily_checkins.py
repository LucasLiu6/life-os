from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.db.client import get_supabase_client
from app.schemas.daily_checkins import DailyCheckinCreate, DailyCheckinResponse


router = APIRouter(prefix="/daily-checkins", tags=["daily-checkins"])


@router.post(
    "",
    response_model=DailyCheckinResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_daily_checkin(checkin: DailyCheckinCreate) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("daily_checkins")
            .insert(checkin.model_dump(mode="json"))
            .execute()
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to create daily check-in.",
        ) from error

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="Supabase returned no created daily check-in.",
        )

    return response.data[0]


@router.get("", response_model=list[DailyCheckinResponse])
def list_daily_checkins(
    limit: int = Query(default=30, ge=1, le=100),
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    try:
        query = (
            get_supabase_client()
            .table("daily_checkins")
            .select("*")
            .order("date", desc=True)
            .order("created_at", desc=True)
        )

        if start_date is not None:
            query = query.gte("date", start_date.isoformat())

        if end_date is not None:
            query = query.lte("date", end_date.isoformat())

        response = query.limit(limit).execute()
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to list daily check-ins.",
        ) from error

    return response.data or []
