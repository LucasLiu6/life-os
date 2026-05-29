from datetime import date, datetime

from pydantic import BaseModel


class GoalCreate(BaseModel):
    domain: str
    title: str
    description: str | None = None
    why_it_matters: str | None = None
    target_date: date | None = None
    status: str = "active"
    weekly_target: str | None = None
    success_metric: str | None = None


class GoalResponse(GoalCreate):
    id: str
    created_at: datetime
    updated_at: datetime
