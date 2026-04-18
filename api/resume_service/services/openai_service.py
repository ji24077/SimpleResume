"""OpenAI API interaction service."""

from openai import OpenAI

from resume_service.config import settings


def get_openai_client() -> OpenAI:
    """Create an OpenAI client with the configured API key."""
    return OpenAI(api_key=settings.openai_api_key)
