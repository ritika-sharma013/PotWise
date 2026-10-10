"""Plant identification through a local Ollama vision model.

This module deliberately contains no Streamlit code and no plant-care facts.
The model proposes an identity; the trusted plants JSON is used only to match
that proposal to an application plant ID when records are available.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

import requests


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma3"
DEFAULT_PLANTS_PATH = Path(__file__).resolve().parents[1] / "data" / "plants.json"


class IdentificationError(RuntimeError):
    """Base error for local plant-identification failures."""


class OllamaUnavailableError(IdentificationError):
    """Raised when Ollama cannot be reached."""


class OllamaModelError(IdentificationError):
    """Raised when the configured Ollama model is unavailable or fails."""


@dataclass(frozen=True)
class IdentificationResult:
    """Validated plant-identification output for the application UI."""

    is_plant: bool
    status: Literal["identified", "uncertain", "not_plant"]
    common_name: str | None
    scientific_name: str | None
    confidence: float | None
    candidates: list[str]
    raw_response: str
    plant_id: str | None

    @property
    def predicted_name(self) -> str:
        """Backward-compatible display name for callers of the old result."""

        return self.common_name or "Unknown plant"


def load_known_plants(path: str | Path = DEFAULT_PLANTS_PATH) -> list[dict[str, Any]]:
    """Load trusted plant records, treating empty or invalid data as unavailable."""

    plants_path = Path(path)
    if not plants_path.exists():
        return []
    try:
        contents = plants_path.read_text(encoding="utf-8").strip()
        if not contents:
            return []
        payload = json.loads(contents)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [plant for plant in payload if isinstance(plant, dict)]


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _match_known_plant(prediction: str, plants: list[dict[str, Any]]) -> tuple[str, str] | None:
    normalised_prediction = _normalise(prediction)
    for plant in plants:
        plant_id = str(plant.get("id", "")).strip()
        aliases = plant.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = []
        names = [plant.get("name", ""), plant_id, *aliases]
        for name in names:
            if name and _normalise(str(name)) == normalised_prediction:
                return plant_id, str(plant.get("name") or plant_id)
    return None


def _normalise_candidates(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    candidates: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip() and item.strip() not in candidates:
            candidates.append(item.strip())
    return candidates


def _clean_json_response(response_text: str) -> str:
    """Remove common Markdown wrapping and isolate a JSON object if possible."""

    text = response_text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    text = text.strip()
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
    return text


def _parse_identification(response_text: str) -> IdentificationResult:
    """Parse and validate model output without allowing bad output to crash the app."""

    uncertain = IdentificationResult(
        is_plant=True,
        status="uncertain",
        common_name=None,
        scientific_name=None,
        confidence=None,
        candidates=[],
        raw_response=response_text,
        plant_id=None,
    )

    try:
        parsed = json.loads(_clean_json_response(response_text))
    except (TypeError, json.JSONDecodeError):
        return uncertain
    if not isinstance(parsed, dict):
        return uncertain

    is_plant = parsed.get("is_plant")
    if is_plant is False or parsed.get("status") == "not_plant":
        return IdentificationResult(
            is_plant=False,
            status="not_plant",
            common_name=None,
            scientific_name=None,
            confidence=None,
            candidates=[],
            raw_response=response_text,
            plant_id=None,
        )
    if is_plant is not True:
        return uncertain

    status = parsed.get("status")
    if status not in {"identified", "uncertain"}:
        status = "uncertain"
    common_name = parsed.get("common_name")
    if not isinstance(common_name, str) or not common_name.strip():
        common_name = None
    elif _normalise(common_name) in {"unknown", "unknown plant", "none", "null"}:
        common_name = None

    scientific_name = parsed.get("scientific_name")
    if not isinstance(scientific_name, str) or not scientific_name.strip():
        scientific_name = None

    confidence = parsed.get("confidence")
    if isinstance(confidence, int | float) and not isinstance(confidence, bool):
        confidence = float(confidence)
        if confidence > 1 and confidence <= 100:
            confidence /= 100
        if not 0 <= confidence <= 1:
            confidence = None
    else:
        confidence = None

    candidates = _normalise_candidates(parsed.get("candidates"))
    if common_name is None or status == "uncertain" or confidence is None or confidence < 0.65:
        status = "uncertain"
    return IdentificationResult(
        is_plant=True,
        status=status,
        common_name=common_name,
        scientific_name=scientific_name,
        confidence=confidence,
        candidates=candidates,
        raw_response=response_text,
        plant_id=None,
    )


def identify_plant(
    image_bytes: bytes,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    plants_path: str | Path = DEFAULT_PLANTS_PATH,
    timeout_seconds: float = 120,
) -> IdentificationResult:
    """Identify an uploaded image using Ollama's local vision endpoint."""

    if not image_bytes:
        raise IdentificationError("The uploaded image is empty.")
    prompt = (
        "Inspect the image and return JSON only, with exactly these fields: "
        "is_plant (boolean), status (identified, uncertain, or not_plant), "
        "common_name (string or null), scientific_name (string or null), "
        "confidence (number from 0 to 1 or null), and candidates (array of strings). "
        "Set not_plant when the image does not show a plant. Set uncertain when "
        "the image is blurry, ambiguous, or insufficient, or confidence is low. "
        "Identify the plant only when reasonably possible. Never provide care advice. "
        "Never include or invent a plant_id; the application assigns trusted IDs."
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [base64.b64encode(image_bytes).decode("ascii")],
        "stream": False,
        "format": "json",
    }
    endpoint = f"{ollama_url.rstrip('/')}/api/generate"
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
    except requests.exceptions.RequestException as exc:
        raise OllamaUnavailableError(
            f"Ollama is unavailable at {ollama_url}. Start Ollama and try again."
        ) from exc
    if response.status_code == 404:
        raise OllamaModelError(
            f"Ollama could not find model '{model}'. Install it with: ollama pull {model}"
        )
    if response.status_code >= 400:
        detail = response.text[:300].strip()
        raise OllamaModelError(f"Ollama returned HTTP {response.status_code}: {detail}")
    try:
        body = response.json()
    except ValueError as exc:
        raise OllamaModelError("Ollama returned an invalid JSON response.") from exc
    if not isinstance(body, dict):
        return _parse_identification("")
    raw_response = body.get("response")
    if not isinstance(raw_response, str) or not raw_response.strip():
        return _parse_identification("")

    result = _parse_identification(raw_response)
    if result.status != "identified" or not result.common_name:
        return result
    plants = load_known_plants(plants_path)
    known_match = None
    for name in [result.common_name, *result.candidates]:
        known_match = _match_known_plant(name, plants)
        if known_match:
            break
    if not known_match:
        return result
    return replace(result, common_name=known_match[1], plant_id=known_match[0])
