import httpx

from app.config import settings


TELEGRAM_MESSAGE_CHUNK_SIZE = 3900


def send_telegram_message(text: str, chat_id: str | None = None) -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError(
            "Missing Telegram configuration. Set TELEGRAM_BOT_TOKEN in your local .env file."
        )

    resolved_chat_id = chat_id or settings.telegram_chat_id
    if not resolved_chat_id:
        raise RuntimeError(
            "Missing Telegram configuration. Set TELEGRAM_CHAT_ID in your local .env file."
        )

    for chunk in _split_message(text):
        response = httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={
                "chat_id": resolved_chat_id,
                "text": chunk,
            },
            timeout=10,
        )
        response.raise_for_status()


def _split_message(text: str) -> list[str]:
    if not text:
        return [""]

    return [
        text[index : index + TELEGRAM_MESSAGE_CHUNK_SIZE]
        for index in range(0, len(text), TELEGRAM_MESSAGE_CHUNK_SIZE)
    ]
