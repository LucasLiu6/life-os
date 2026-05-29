from datetime import date, datetime

from pydantic import BaseModel, Field


class DailyCheckinCreate(BaseModel):
    date: date
    planned_top_3: str | None = None
    completed: str | None = None
    blockers: str | None = None
    energy_level: int | None = Field(default=None, ge=1, le=10)
    mood: str | None = None
    notes: str | None = None
    tomorrow_focus: str | None = None


class DailyCheckinResponse(DailyCheckinCreate):
    id: str
    created_at: datetime
