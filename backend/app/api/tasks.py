from fastapi import APIRouter, HTTPException, status

from app.db.client import get_supabase_client
from app.schemas.tasks import TaskCreate, TaskResponse


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate) -> dict:
    try:
        response = (
            get_supabase_client()
            .table("tasks")
            .insert(task.model_dump(mode="json"))
            .execute()
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Failed to create task.") from error

    if not response.data:
        raise HTTPException(status_code=500, detail="Supabase returned no created task.")

    return response.data[0]


@router.get("", response_model=list[TaskResponse])
def list_tasks() -> list[dict]:
    try:
        response = (
            get_supabase_client()
            .table("tasks")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Failed to list tasks.") from error

    return response.data or []
