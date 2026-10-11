"""Optional ElevenLabs text-to-speech support for assistant responses."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path


_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
_last_voice_error: str | None = None


def _load_env_file() -> None:
    if not _ENV_PATH.exists():
        return
    try:
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        match = re.match(r"^\s*(ELEVENLABS_API_KEY|ELEVENLABS_VOICE_ID)\s*=\s*(.*)\s*$", line)
        if not match:
            continue
        value = match.group(2).strip().strip("'\"")
        os.environ.setdefault(match.group(1), value)


def _record_error(error: BaseException) -> None:
    message = str(error) or "No error message returned."
    for secret_name in ("ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID"):
        secret = os.getenv(secret_name)
        if secret:
            message = message.replace(secret, "[redacted]")
    message = re.sub(
        r"(?i)(authorization|x-api-key|api-key)\s*[:=]\s*[^,;}\s]+",
        r"\1: [redacted]",
        message,
    )
    status_code = getattr(error, "status_code", None)
    status = f" (status {status_code})" if isinstance(status_code, int) else ""
    global _last_voice_error
    _last_voice_error = f"{type(error).__name__}: {message[:300]}{status}"


def get_last_voice_error() -> str | None:
    """Return the latest safe diagnostic for the UI."""

    return _last_voice_error


def text_to_speech(text: str) -> bytes | None:
    """Convert assistant text to MP3 bytes, returning None when unavailable."""

    global _last_voice_error
    _last_voice_error = None
    _load_env_file()
    if not isinstance(text, str) or not text.strip():
        _last_voice_error = "ValueError: Assistant response is empty."
        return None
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if not api_key:
        _last_voice_error = "ConfigurationError: ELEVENLABS_API_KEY is not configured."
        return None
    if not voice_id:
        _last_voice_error = "ConfigurationError: ELEVENLABS_VOICE_ID is not configured."
        return None

    try:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=api_key)
        audio = client.text_to_speech.convert(
            text=text.strip(),
            voice_id=voice_id,
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128",
        )
        if isinstance(audio, bytes):
            return audio or None
        if isinstance(audio, Iterable):
            audio_bytes = b"".join(
                bytes(chunk)
                for chunk in audio
                if isinstance(chunk, (bytes, bytearray, memoryview))
            )
            if audio_bytes:
                return audio_bytes
            _last_voice_error = "ResponseError: ElevenLabs returned no audio bytes."
            return None
        _last_voice_error = "ResponseError: ElevenLabs returned no audio bytes."
    except Exception as error:
        _record_error(error)
        return None
    return None


def speech_to_text(audio_bytes: bytes) -> str | None:
    """Transcribe microphone audio with ElevenLabs, returning text or None."""

    global _last_voice_error
    _last_voice_error = None
    _load_env_file()
    if not isinstance(audio_bytes, bytes) or not audio_bytes:
        _last_voice_error = "ValueError: Microphone audio is empty."
        return None
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        _last_voice_error = "ConfigurationError: ELEVENLABS_API_KEY is not configured."
        return None

    try:
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=api_key)
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "potwise-recording.webm"
        transcription = client.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v2",
        )
        text = getattr(transcription, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()
        if isinstance(transcription, dict):
            text = transcription.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()
        _last_voice_error = "ResponseError: ElevenLabs returned no transcript."
    except Exception as error:
        _record_error(error)
    return None
