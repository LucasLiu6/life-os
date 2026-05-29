from fastapi import APIRouter, HTTPException

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
