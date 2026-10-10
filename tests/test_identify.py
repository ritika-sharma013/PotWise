import json

from core.identify import _match_known_plant, _parse_identification, load_known_plants


def test_parses_identified_json_and_ignores_model_plant_id() -> None:
    result = _parse_identification(
        json.dumps(
            {
                "is_plant": True,
                "status": "identified",
                "common_name": "Rose",
                "scientific_name": "Rosa",
                "confidence": 0.92,
                "candidates": ["Rose", "Hibiscus"],
                "plant_id": "invented-id",
            }
        )
    )

    assert result.status == "identified"
    assert result.common_name == "Rose"
    assert result.plant_id is None


def test_parses_markdown_wrapped_non_plant_response() -> None:
    result = _parse_identification('```json\n{"is_plant": false, "status": "not_plant"}\n```')

    assert result.status == "not_plant"
    assert result.is_plant is False


def test_malformed_or_unknown_response_becomes_uncertain() -> None:
    malformed = _parse_identification("not JSON")
    unknown = _parse_identification(
        '{"is_plant": true, "status": "identified", "common_name": "Unknown plant", "confidence": 0.99}'
    )

    assert malformed.status == "uncertain"
    assert unknown.status == "uncertain"
    assert unknown.common_name is None


def test_low_confidence_response_is_uncertain() -> None:
    result = _parse_identification(
        '{"is_plant": true, "status": "identified", "common_name": "Rose", "confidence": 0.4}'
    )

    assert result.status == "uncertain"


def test_known_plant_matching_requires_exact_normalized_name() -> None:
    plants = [{"id": "rose", "name": "Rose", "aliases": ["Garden rose"]}]

    assert _match_known_plant(" garden-rose ", plants) == ("rose", "Rose")
    assert _match_known_plant("Rose plant", plants) is None


def test_empty_or_malformed_plants_file_is_unavailable(tmp_path) -> None:
    empty = tmp_path / "empty.json"
    malformed = tmp_path / "malformed.json"
    empty.write_text("", encoding="utf-8")
    malformed.write_text("not json", encoding="utf-8")

    assert load_known_plants(empty) == []
    assert load_known_plants(malformed) == []
