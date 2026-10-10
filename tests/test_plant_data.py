import json

from core.plant_data import (
    find_plant_by_name,
    get_plant_by_id,
    get_supported_plants,
    load_plants,
)


def _write_plants(tmp_path, payload: object, name: str = "plants.json"):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_loads_valid_plant_list_and_supported_plants(tmp_path) -> None:
    plants = [{"id": "rose", "name": "Rose"}]
    path = _write_plants(tmp_path, plants)

    assert load_plants(path) == plants
    assert get_supported_plants(path) == plants
    assert get_plant_by_id("ROSE", path) == plants[0]


def test_empty_missing_and_malformed_files_are_unavailable(tmp_path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not json", encoding="utf-8")

    assert load_plants(empty) == []
    assert load_plants(tmp_path / "missing.json") == []
    assert load_plants(malformed) == []
    assert load_plants(_write_plants(tmp_path, {"not": "a list"}, "object.json")) == []


def test_matches_exact_name_scientific_name_and_alias(tmp_path) -> None:
    plants = [
        {
            "id": "rose",
            "name": "Rose",
            "scientific_name": "Rosa rubiginosa",
            "aliases": ["Garden rose"],
        }
    ]
    path = _write_plants(tmp_path, plants)

    assert find_plant_by_name("rose", path) == plants[0]
    assert find_plant_by_name("rosa rubiginosa", path) == plants[0]
    assert find_plant_by_name("GARDEN-ROSE", path) == plants[0]


def test_unsupported_and_substring_names_do_not_match(tmp_path) -> None:
    plants = [{"id": "rose", "name": "Rose", "aliases": ["Garden rose"]}]
    path = _write_plants(tmp_path, plants)

    assert find_plant_by_name("Orchid", path) is None
    assert find_plant_by_name("Rose plant", path) is None
    assert get_plant_by_id("rose-extra", path) is None
