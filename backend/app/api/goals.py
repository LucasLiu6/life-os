from fastapi import APIRouter, HTTPException, status

from app.db.client import get_supabase_client
from app.schemas.goals import GoalCreate, GoalResponse


router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def create_goal(goal: GoalCreate) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("goals")
            .insert(goal.model_dump(mode="json"))
            .execute()
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Failed to create goal.") from error

    if not response.data:
        raise HTTPException(status_code=500, detail="Supabase returned no created goal.")

    return response.data[0]


@router.get("", response_model=list[GoalResponse])
def list_goals() -> list[dict]:
    try:
        response = (
            get_supabase_client()
            .table("goals")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Failed to list goals.") from error

    return response.data or []
