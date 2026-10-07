"""Plant identification through a local Ollama vision model.

This module deliberately contains no Streamlit code and no plant-care facts.
The model proposes an identity; the trusted plants JSON is used only to match
that proposal to an application plant ID when records are available.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    """The model prediction and its optional trusted-data match."""

    predicted_name: str
    plant_id: str | None
    raw_response: str


def load_known_plants(path: str | Path = DEFAULT_PLANTS_PATH) -> list[dict[str, Any]]:
    """Load plant records without modifying or enriching the trusted JSON."""

    plants_path = Path(path)
    if not plants_path.exists():
        return []
    try:
        payload = json.loads(plants_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentificationError(f"Could not read plant data: {exc}") from exc
    if not isinstance(payload, list):
        raise IdentificationError("Plant data must contain a JSON list.")
    return [plant for plant in payload if isinstance(plant, dict)]


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _match_known_plant(prediction: str, plants: list[dict[str, Any]]) -> tuple[str, str] | None:
    normalised_prediction = _normalise(prediction)
    for plant in plants:
        plant_id = str(plant.get("id", "")).strip()
        names = [plant.get("name", ""), plant_id, *(plant.get("aliases", []) or [])]
        for name in names:
            if name and _normalise(str(name)) in normalised_prediction:
                return plant_id, str(plant.get("name") or plant_id)
    return None


def _parse_prediction(response_text: str) -> str:
    """Extract a concise plant name from common Gemma response formats."""

    text = response_text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        for key in ("plant_id", "plant_name", "name", "prediction"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    text = re.sub(r"```(?:json)?|```", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^(?:plant\s*(?:name|identified as|is)\s*:\s*)", "", text, flags=re.IGNORECASE)
    return text.splitlines()[0].strip(" -*\t") or "Unknown plant"


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
        "Identify the plant in this image. Reply with only the most likely common "
        "plant name, or Unknown plant if you cannot identify it. Do not provide "
        "care advice."
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [base64.b64encode(image_bytes).decode("ascii")],
        "stream": False,
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
    raw_response = body.get("response")
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise OllamaModelError("Ollama returned no plant identification.")

    predicted_name = _parse_prediction(raw_response)
    known_match = _match_known_plant(predicted_name, load_known_plants(plants_path))
    plant_id = known_match[0] if known_match else None
    if known_match:
        predicted_name = known_match[1]
    return IdentificationResult(predicted_name, plant_id, raw_response)
