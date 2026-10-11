from database.db import list_saved_pots, save_pot


def test_save_and_list_pots(tmp_path) -> None:
    database_path = tmp_path / "pots.sqlite3"

    assert save_pot(
        "aloe_vera",
        "Aloe Vera",
        "Aloe vera",
        3.0,
        database_path=database_path,
    ) is True
    assert list_saved_pots(database_path=database_path) == [
        {
            "plant_id": "aloe_vera",
            "plant_name": "Aloe Vera",
            "scientific_name": "Aloe vera",
            "pot_volume_litres": 3.0,
        }
    ]


def test_duplicate_plant_is_not_saved_twice(tmp_path) -> None:
    database_path = tmp_path / "pots.sqlite3"

    assert save_pot("aloe_vera", "Aloe Vera", database_path=database_path) is True
    assert save_pot("aloe_vera", "Aloe Vera", database_path=database_path) is False
    assert len(list_saved_pots(database_path=database_path)) == 1
