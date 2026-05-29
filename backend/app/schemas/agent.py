from datetime import date as date_type

from pydantic import BaseModel, Field

from app.schemas.daily_checkins import DailyCheckinResponse


class ParseEveningReplyRequest(BaseModel):
    reply: str = Field(..., min_length=1)
    date: date_type | None = None


class ParseEveningReplyResponse(BaseModel):
    parsed_checkin: DailyCheckinResponse
