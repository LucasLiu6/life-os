from datetime import date, datetime

from pydantic import BaseModel


class TaskCreate(BaseModel):
    domain: str
    title: str
    description: str | None = None
    due_date: date | None = None
    priority: str = "medium"
    status: str = "open"
    estimated_minutes: int | None = None
    source: str | None = None
    related_goal_id: str | None = None


class TaskResponse(TaskCreate):
    id: str
    created_at: datetime
    updated_at: datetime
