"""Bounded browser microphone component for the Mic Assistant."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components


_COMPONENT_PATH = Path(__file__).resolve().parents[1] / "components" / "mic_recorder"
_record_microphone = components.declare_component(
    "potwise_mic_recorder",
    path=str(_COMPONENT_PATH),
)


def record_microphone(*, key: str) -> Any:
    """Render the recorder and return only a completed recording payload."""

    return _record_microphone(key=key, default=None)
