from core.pots import (
    delete_pot,
    get_or_create_conversation,
    list_saved_pots,
    load_conversation_messages,
    save_conversation_message,
    save_pot,
)


def test_save_and_load_pots(tmp_path) -> None:
    database_path = tmp_path / "potwise.db"

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


def test_duplicate_save_is_ignored(tmp_path) -> None:
    database_path = tmp_path / "potwise.db"

    assert save_pot("aloe_vera", "Aloe Vera", database_path=database_path) is True
    assert save_pot("aloe_vera", "Aloe Vera", database_path=database_path) is False
    assert len(list_saved_pots(database_path=database_path)) == 1


def test_delete_pot(tmp_path) -> None:
    database_path = tmp_path / "potwise.db"
    save_pot("aloe_vera", "Aloe Vera", database_path=database_path)

    assert delete_pot("aloe_vera", database_path=database_path) is True
    assert list_saved_pots(database_path=database_path) == []
    assert delete_pot("aloe_vera", database_path=database_path) is False


def test_conversation_messages_round_trip(tmp_path) -> None:
    database_path = tmp_path / "potwise.db"

    conversation_id = get_or_create_conversation("aloe_vera", database_path=database_path)
    assert get_or_create_conversation("aloe_vera", database_path=database_path) == conversation_id

    save_conversation_message(
        conversation_id,
        "user",
        "My leaves are yellow.",
        "voice",
        database_path=database_path,
    )
    save_conversation_message(
        conversation_id,
        "assistant",
        "One possible cause is excess moisture.",
        "voice",
        database_path=database_path,
    )

    messages = load_conversation_messages(conversation_id, database_path=database_path)
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert [message["message_text"] for message in messages] == [
        "My leaves are yellow.",
        "One possible cause is excess moisture.",
    ]
    assert [message["input_method"] for message in messages] == ["voice", "voice"]
    assert all(message["timestamp"] for message in messages)
