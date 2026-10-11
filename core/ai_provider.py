"""Provider selection for PotWise's local and deployed AI backends."""

from __future__ import annotations

import json
import os
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from core.assistant import (
    _build_system_prompt,
    _trim_messages,
    chat_with_gemma,
)
from core.identify import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_PLANTS_PATH,
    IdentificationError,
    IdentificationResult,
    _clean_json_response,
    _match_known_plant,
    _parse_identification,
    identify_plant,
    load_known_plants,
)


DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"


class GeminiProviderError(RuntimeError):
    """Base class for safe, user-facing Gemini provider errors."""


class GeminiConfigurationError(GeminiProviderError):
    """Raised when Gemini is not configured for use."""


class GeminiResponseError(GeminiProviderError):
    """Raised when Gemini returns an unusable response."""


def _streamlit_secret(name: str) -> str | None:
    """Read one Streamlit secret without requiring Streamlit at import time."""

    try:
        import streamlit as st

        value = st.secrets.get(name)
    except Exception:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _configuration_value(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or _streamlit_secret(name) or default


def _gemini_api_key() -> str | None:
    """Prefer Streamlit secrets, with an environment fallback for local use."""

    return _streamlit_secret("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")


def _provider_name() -> str:
    provider = _configuration_value("AI_PROVIDER", "ollama")
    return (provider or "ollama").strip().lower()


def _load_gemini_sdk() -> tuple[Any, Any]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise GeminiConfigurationError(
            "Gemini support requires the google-genai package."
        ) from exc
    return genai, types


def _gemini_client() -> tuple[Any, Any]:
    api_key = _gemini_api_key()
    if not api_key:
        raise GeminiConfigurationError(
            "Gemini is not configured. Add GEMINI_API_KEY to Streamlit secrets "
            "or the environment."
        )
    genai, types = _load_gemini_sdk()
    try:
        client = genai.Client(api_key=api_key)
    except Exception as exc:
        raise GeminiConfigurationError("Gemini could not be configured.") from exc
    return client, types


def _gemini_model() -> str:
    return _configuration_value("GEMINI_MODEL", DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL


def _safe_gemini_request_error(exc: Exception) -> GeminiProviderError:
    """Convert SDK failures to useful messages without exposing secrets."""

    raw_detail = str(exc)
    api_key = _gemini_api_key()
    if api_key:
        raw_detail = raw_detail.replace(api_key, "[REDACTED]")
    detail = re.sub(
        r"(?i)(authorization|x-goog-api-key)\s*[:=]\s*[^\s,}]+",
        r"\1: [REDACTED]",
        raw_detail,
    )
    detail = re.sub(
        r"(?i)([?&](?:key|api_key)=)[^&\s]+",
        r"\1[REDACTED]",
        detail,
    )[:1200]
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    status_text = f" status={status}" if status is not None else ""
    diagnostic = f"{type(exc).__name__}{status_text}: {detail}"
    lowered = detail.lower()
    if status in {401, 403} or "api key" in lowered or "permission" in lowered:
        return GeminiConfigurationError(f"Gemini authentication failed — {diagnostic}")
    return GeminiProviderError(f"Gemini request failed — {diagnostic}")


def _image_mime_type(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _gemini_identification_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "is_plant": {"type": "BOOLEAN"},
            "status": {
                "type": "STRING",
                "enum": ["identified", "uncertain", "not_plant"],
            },
            "common_name": {"type": "STRING", "nullable": True},
            "scientific_name": {"type": "STRING", "nullable": True},
            "confidence": {"type": "NUMBER", "nullable": True},
            "candidates": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": [
            "is_plant",
            "status",
            "common_name",
            "scientific_name",
            "confidence",
            "candidates",
        ],
    }


def _trusted_identification_result(
    result: IdentificationResult,
    plants_path: str | Path,
) -> IdentificationResult:
    if result.status != "identified" or not result.common_name:
        return result
    plants = load_known_plants(plants_path)
    for name in [result.common_name, *result.candidates]:
        known_match = _match_known_plant(name, plants)
        if known_match:
            plant_id, common_name = known_match
            return replace(result, common_name=common_name, plant_id=plant_id)
    return result


def _identify_with_gemini(
    image_bytes: bytes,
    *,
    plants_path: str | Path,
) -> IdentificationResult:
    if not image_bytes:
        raise IdentificationError("The uploaded image is empty.")

    client, types = _gemini_client()
    prompt = (
        "Inspect the image and return JSON only, with exactly these fields: "
        "is_plant (boolean), status (identified, uncertain, or not_plant), "
        "common_name (string or null), scientific_name (string or null), "
        "confidence (number from 0 to 1 or null), and candidates (array of strings). "
        "Set not_plant when the image does not show a plant. Set uncertain when "
        "the image is blurry, ambiguous, or insufficient, or confidence is low. "
        "Identify the plant only when reasonably possible. Never provide care advice. "
        "Never provide or invent a plant_id; the application assigns trusted IDs."
    )
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=_image_mime_type(image_bytes)),
        prompt,
    ]
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=_gemini_identification_schema(),
    )
    try:
        response = client.models.generate_content(
            model=_gemini_model(),
            contents=contents,
            config=config,
        )
    except Exception as exc:
        raise _safe_gemini_request_error(exc) from exc

    raw_response = getattr(response, "text", None)
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise GeminiResponseError("Gemini returned an empty identification response.")
    try:
        parsed = json.loads(_clean_json_response(raw_response))
    except (TypeError, json.JSONDecodeError) as exc:
        raise GeminiResponseError("Gemini returned malformed identification data.") from exc
    if not isinstance(parsed, dict):
        raise GeminiResponseError("Gemini returned malformed identification data.")
    result = _parse_identification(raw_response)
    return _trusted_identification_result(result, plants_path)


def _gemini_chat_contents(types: Any, messages: list[dict[str, str]]) -> list[Any]:
    contents: list[Any] = []
    for message in _trim_messages(messages):
        role = "user" if message["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=message["content"])],
            )
        )
    return contents


def _chat_with_gemini(
    messages: list[dict[str, str]],
    plant_context: dict[str, Any] | None,
    problem_context: Any,
) -> str:
    contents_client, types = _gemini_client()
    contents = _gemini_chat_contents(types, messages)
    if not contents:
        raise GeminiResponseError("No conversation message was provided to Gemini.")
    config = types.GenerateContentConfig(
        system_instruction=_build_system_prompt(plant_context, problem_context),
    )
    try:
        response = contents_client.models.generate_content(
            model=_gemini_model(),
            contents=contents,
            config=config,
        )
    except Exception as exc:
        raise _safe_gemini_request_error(exc) from exc
    assistant_text = getattr(response, "text", None)
    if not isinstance(assistant_text, str) or not assistant_text.strip():
        raise GeminiResponseError("Gemini returned an empty assistant response.")
    return assistant_text.strip()


def identify_plant_with_provider(
    image_bytes: bytes,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    plants_path: str | Path = DEFAULT_PLANTS_PATH,
    timeout_seconds: float = 120,
) -> IdentificationResult:
    """Identify a plant using the configured AI provider."""

    provider = _provider_name()
    if provider == "ollama":
        return identify_plant(
            image_bytes,
            model=model,
            ollama_url=ollama_url,
            plants_path=plants_path,
            timeout_seconds=timeout_seconds,
        )
    if provider == "gemini":
        return _identify_with_gemini(image_bytes, plants_path=plants_path)
    raise GeminiConfigurationError(
        f"Unsupported AI_PROVIDER '{provider}'. Use 'ollama' or 'gemini'."
    )


def chat_with_provider(
    messages: list[dict[str, str]],
    plant_context: dict[str, Any] | None,
    problem_context: Any,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout_seconds: float = 120,
) -> str:
    """Continue a grounded assistant conversation using the configured provider."""

    provider = _provider_name()
    if provider == "ollama":
        return chat_with_gemma(
            messages,
            plant_context,
            problem_context,
            model=model,
            ollama_url=ollama_url,
            timeout_seconds=timeout_seconds,
        )
    if provider == "gemini":
        return _chat_with_gemini(messages, plant_context, problem_context)
    raise GeminiConfigurationError(
        f"Unsupported AI_PROVIDER '{provider}'. Use 'ollama' or 'gemini'."
    )


__all__ = [
    "GeminiConfigurationError",
    "GeminiProviderError",
    "GeminiResponseError",
    "chat_with_provider",
    "identify_plant_with_provider",
]
