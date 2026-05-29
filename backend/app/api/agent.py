from fastapi import APIRouter, HTTPException

from app.schemas.agent import ParseEveningReplyRequest, ParseEveningReplyResponse
from app.services.evening_checkin import generate_evening_checkin
from app.services.evening_reply_parser import parse_evening_reply
from app.services.morning_briefing import generate_morning_briefing


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/morning-briefing")
def create_morning_briefing() -> dict[str, str]:
    try:
        briefing = generate_morning_briefing()
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate morning briefing.",
        ) from error

    return {"briefing": briefing}


@router.post("/evening-checkin")
def create_evening_checkin() -> dict[str, str]:
    try:
        message = generate_evening_checkin()
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate evening check-in.",
        ) from error

    return {"message": message}


@router.post("/parse-evening-reply", response_model=ParseEveningReplyResponse)
def create_parsed_evening_reply(
    request: ParseEveningReplyRequest,
) -> dict:
    try:
        parsed_checkin = parse_evening_reply(request.reply, request.date)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to parse evening reply.",
        ) from error

    return {"parsed_checkin": parsed_checkin}
