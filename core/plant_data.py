"""Read-only access to trusted plant records."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_PLANTS_PATH = Path(__file__).resolve().parents[1] / "data" / "plants.json"
PlantRecord = dict[str, Any]


def _normalise(value: str) -> str:
    """Normalize a lookup value without changing the stored plant record."""

    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def load_plants(path: str | Path = DEFAULT_PLANTS_PATH) -> list[PlantRecord]:
    """Load trusted plant records, returning no records for unavailable data."""

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


def _matches_value(value: Any, query: str) -> bool:
    return isinstance(value, str) and bool(query) and _normalise(value) == query


def _plant_aliases(plant: PlantRecord) -> list[Any]:
    aliases = plant.get("aliases", [])
    return aliases if isinstance(aliases, list) else []


def _matches_name(plant: PlantRecord, name: str) -> bool:
    query = _normalise(name)
    if not query:
        return False
    values = [
        plant.get("id"),
        plant.get("name"),
        plant.get("scientific_name"),
        *_plant_aliases(plant),
    ]
    return any(_matches_value(value, query) for value in values)


def get_plant_by_id(plant_id: str, path: str | Path = DEFAULT_PLANTS_PATH) -> PlantRecord | None:
    """Return the trusted record whose normalized ID exactly matches ``plant_id``."""

    query = _normalise(plant_id)
    if not query:
        return None
    for plant in load_plants(path):
        if _matches_value(plant.get("id"), query):
            return plant
    return None


def find_plant_by_name(name: str, path: str | Path = DEFAULT_PLANTS_PATH) -> PlantRecord | None:
    """Find a record by exact normalized ID, name, scientific name, or alias."""

    for plant in load_plants(path):
        if _matches_name(plant, name):
            return plant
    return None


def get_supported_plants(path: str | Path = DEFAULT_PLANTS_PATH) -> list[PlantRecord]:
    """Return the trusted records available for confirmation or manual selection."""

    return load_plants(path)
