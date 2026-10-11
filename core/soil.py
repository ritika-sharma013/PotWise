"""Soil-mix calculations based on trusted plant-record ratios."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


def calculate_soil_mix(
    plant: Mapping[str, Any], total_volume_litres: float
) -> list[dict[str, float | str]]:
    """Return each soil component's volume for the requested total volume.

    The plant record's ``soil_mix_parts`` values are treated as relative parts;
    no plant-specific ratio is created or changed here. Invalid or unavailable
    soil data returns an empty list so callers can show a safe fallback.
    """

    if not isinstance(plant, Mapping):
        return []
    if isinstance(total_volume_litres, bool) or not isinstance(
        total_volume_litres, (int, float)
    ):
        return []
    if not math.isfinite(float(total_volume_litres)) or total_volume_litres <= 0:
        return []

    soil_mix_parts = plant.get("soil_mix_parts")
    if not isinstance(soil_mix_parts, Mapping) or not soil_mix_parts:
        return []

    valid_parts: list[tuple[str, float]] = []
    for component, parts in soil_mix_parts.items():
        if not isinstance(component, str) or not component.strip():
            return []
        if isinstance(parts, bool) or not isinstance(parts, (int, float)):
            return []
        parts_value = float(parts)
        if not math.isfinite(parts_value) or parts_value <= 0:
            return []
        valid_parts.append((component, parts_value))

    total_parts = sum(parts for _, parts in valid_parts)
    if not valid_parts or total_parts <= 0:
        return []

    total_volume = float(total_volume_litres)
    return [
        {"component": component, "litres": total_volume * parts / total_parts}
        for component, parts in valid_parts
    ]
