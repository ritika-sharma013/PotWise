import pytest

import core.ai_provider as ai_provider


def test_default_provider_delegates_identification_to_ollama(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    expected = object()

    monkeypatch.setattr(ai_provider, "identify_plant", lambda image_bytes, **kwargs: expected)

    assert ai_provider.identify_plant_with_provider(b"image") is expected


def test_default_provider_delegates_chat_to_ollama(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    expected = "local response"

    monkeypatch.setattr(
        ai_provider,
        "chat_with_gemma",
        lambda messages, plant_context, problem_context, **kwargs: expected,
    )

    assert ai_provider.chat_with_provider([], {}, []) == expected


def test_gemini_requires_an_api_key(monkeypatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setattr(ai_provider, "_gemini_api_key", lambda: None)

    with pytest.raises(ai_provider.GeminiConfigurationError, match="GEMINI_API_KEY"):
        ai_provider.chat_with_provider(
            [{"role": "user", "content": "Hello"}],
            {},
            [],
        )
