import re
from urllib.parse import quote

import httpx

from config import get_settings
from errors import AIServiceError

_MODEL_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


async def generate_content(
    prompt: str, *, response_mime_type: str | None = None
) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise AIServiceError(
            "Gemini is not configured. Add GEMINI_API_KEY to your .env file, "
            "or select the local explanation provider for explanations.",
            status_code=503,
        )
    if not _MODEL_NAME.fullmatch(settings.gemini_model):
        raise AIServiceError(
            "GEMINI_MODEL must be a model name containing only letters, digits, "
            "periods, underscores, or hyphens.",
            status_code=500,
        )

    generation_config: dict[str, object] = {
        "temperature": 0.2,
        "maxOutputTokens": 2048,
    }
    if response_mime_type:
        generation_config["responseMimeType"] = response_mime_type

    url = f"{_API_BASE_URL}/{quote(settings.gemini_model, safe='')}:generateContent"
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=10.0)
        ) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.gemini_api_key},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": generation_config,
                },
            )
    except httpx.TimeoutException as exc:
        raise AIServiceError(
            "Gemini did not respond in time. Please try again."
        ) from exc
    except httpx.RequestError as exc:
        raise AIServiceError(
            "Could not connect to Gemini. Check your internet connection and try again."
        ) from exc

    if response.status_code in (401, 403):
        raise AIServiceError(
            "Gemini rejected the API key. Check that GEMINI_API_KEY is valid and "
            "that the Gemini API is enabled."
        )
    if response.status_code == 429:
        raise AIServiceError(
            "Gemini's request limit has been reached. Wait a moment and try again.",
            status_code=429,
        )
    if response.status_code >= 500:
        raise AIServiceError(
            "Gemini is temporarily unavailable. Please try again later.",
            status_code=502,
        )
    if not response.is_success:
        raise AIServiceError(
            f"Gemini rejected the request (HTTP {response.status_code}). "
            "Check the model name and request, then try again.",
            status_code=502,
        )

    try:
        data = response.json()
        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]
        text = "".join(part["text"] for part in parts if isinstance(part, dict) and "text" in part)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise AIServiceError(
            "Gemini returned an unexpected response. Please try again."
        ) from exc

    if not text.strip():
        raise AIServiceError(
            "Gemini did not generate a response. Please rephrase your request."
        )
    return text.strip()
