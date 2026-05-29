from openai import OpenAI

from app.config import settings


def get_openai_client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "Missing OpenAI configuration. Set OPENAI_API_KEY in your local .env file."
        )

    return OpenAI(api_key=settings.openai_api_key)
