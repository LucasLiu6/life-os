from fastapi import APIRouter, HTTPException

from app.services.evening_checkin import generate_evening_checkin
from app.services.evening_reply_parser import parse_evening_reply
from app.services.morning_briefing import generate_morning_briefing
from app.services.weekly_review import generate_weekly_review
from app.telegram.client import send_telegram_message


router = APIRouter(prefix="/telegram", tags=["telegram"])

WELCOME_MESSAGE = (
    "Welcome to Life OS. Available commands: /morning, /evening, /weekly."
)
HELP_MESSAGE = "Available commands: /morning, /evening, /weekly."
CHECKIN_PARSE_ERROR_MESSAGE = (
    "I could not save that check-in. Try replying with what you completed, "
    "blockers, energy 1-10, and tomorrow's focus."
)


@router.post("/send-test-message")
def send_test_message() -> dict[str, str]:
    try:
        send_telegram_message("Life OS test message.")
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to send Telegram test message.",
        ) from error

    return {"status": "sent"}


@router.post("/webhook")
def handle_telegram_webhook(update: dict) -> dict[str, str]:
    # TODO: Use a secret webhook path or Telegram secret token before production.
    chat_id = _extract_chat_id(update)
    text = _extract_message_text(update)

    if chat_id is None or text is None:
        return {"status": "ignored"}

    stripped_text = text.strip()
    if not stripped_text:
        return {"status": "ignored"}

    try:
        response_text = (
            _handle_command(stripped_text)
            if _is_command(stripped_text)
            else _handle_free_text_reply(stripped_text)
        )
        send_telegram_message(response_text, chat_id=str(chat_id))
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Failed to handle Telegram webhook.",
        ) from error

    return {"status": "handled"}


def _is_command(text: str) -> bool:
    return text.startswith("/")


def _handle_command(text: str) -> str:
    command = text.strip().split()[0].lower() if text.strip() else ""

    if command == "/start":
        return WELCOME_MESSAGE
    if command == "/morning":
        return generate_morning_briefing()
    if command == "/evening":
        return generate_evening_checkin()
    if command == "/weekly":
        return generate_weekly_review(None, None)

    return HELP_MESSAGE


def _handle_free_text_reply(text: str) -> str:
    try:
        parsed_checkin = parse_evening_reply(reply=text, checkin_date=None)
    except Exception:
        return CHECKIN_PARSE_ERROR_MESSAGE

    return _build_checkin_confirmation(parsed_checkin)


def _build_checkin_confirmation(parsed_checkin: dict) -> str:
    lines = ["✅ Check-in saved."]
    _append_optional_line(lines, "Energy", parsed_checkin.get("energy_level"))
    _append_optional_line(lines, "Completed", parsed_checkin.get("completed"))
    _append_optional_line(lines, "Blockers", parsed_checkin.get("blockers"))
    _append_optional_line(lines, "Tomorrow", parsed_checkin.get("tomorrow_focus"))
    return "\n".join(lines)


def _append_optional_line(lines: list[str], label: str, value) -> None:
    if value is None:
        return

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return

    lines.append(f"{label}: {value}")


def _extract_chat_id(update: dict) -> int | str | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    chat = message.get("chat")
    if not isinstance(chat, dict):
        return None

    return chat.get("id")


def _extract_message_text(update: dict) -> str | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    text = message.get("text")
    if not isinstance(text, str):
        return None

    return text
