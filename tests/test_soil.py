from core.soil import calculate_soil_mix


def test_calculates_equal_parts() -> None:
    plant = {"soil_mix_parts": {"potting_mix": 1, "perlite": 1, "pumice": 1}}

    assert calculate_soil_mix(plant, 3) == [
        {"component": "potting_mix", "litres": 1.0},
        {"component": "perlite", "litres": 1.0},
        {"component": "pumice", "litres": 1.0},
    ]


def test_calculates_proportional_parts() -> None:
    plant = {"soil_mix_parts": {"potting_mix": 2, "perlite": 1}}

    assert calculate_soil_mix(plant, 6) == [
        {"component": "potting_mix", "litres": 4.0},
        {"component": "perlite", "litres": 2.0},
    ]


def test_missing_or_invalid_soil_data_returns_empty_result() -> None:
    assert calculate_soil_mix({}, 3) == []
    assert calculate_soil_mix({"soil_mix_parts": {"perlite": 0}}, 3) == []
    assert calculate_soil_mix({"soil_mix_parts": {"perlite": "one"}}, 3) == []
    assert calculate_soil_mix({"soil_mix_parts": {}}, 3) == []
