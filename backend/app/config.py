import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    return int(value)


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "life-os-backend")
    app_env: str = os.getenv("APP_ENV", "local")
    log_level: str = os.getenv("LOG_LEVEL", "info")
    supabase_url: str | None = os.getenv("SUPABASE_URL")
    supabase_service_role_key: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.2")
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str | None = os.getenv("TELEGRAM_CHAT_ID")
    scheduler_enabled: bool = _get_bool("SCHEDULER_ENABLED", False)
    timezone: str = os.getenv("TIMEZONE", "America/New_York")
    morning_briefing_hour: int = _get_int("MORNING_BRIEFING_HOUR", 8)
    morning_briefing_minute: int = _get_int("MORNING_BRIEFING_MINUTE", 30)
    evening_checkin_hour: int = _get_int("EVENING_CHECKIN_HOUR", 22)
    evening_checkin_minute: int = _get_int("EVENING_CHECKIN_MINUTE", 30)
    weekly_review_day_of_week: str = os.getenv("WEEKLY_REVIEW_DAY_OF_WEEK", "sun")
    weekly_review_hour: int = _get_int("WEEKLY_REVIEW_HOUR", 20)
    weekly_review_minute: int = _get_int("WEEKLY_REVIEW_MINUTE", 0)


settings = Settings()
