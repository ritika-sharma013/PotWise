from core.chat_history import (
    create_conversation,
    get_conversation,
    get_conversation_messages,
    list_recent_conversations,
    save_message,
    update_conversation,
)


def test_same_plant_creates_distinct_conversations(tmp_path) -> None:
    database_path = tmp_path / "potwise.db"

    first = create_conversation("rose", "Rose", database_path=database_path)
    second = create_conversation("rose", "Rose", database_path=database_path)

    assert first != second
    assert [chat["id"] for chat in list_recent_conversations(database_path=database_path)] == [
        second,
        first,
    ]


def test_messages_persist_and_update_recent_chat(tmp_path) -> None:
    database_path = tmp_path / "potwise.db"
    conversation_id = create_conversation("aloe_vera", "Aloe Vera", database_path=database_path)

    save_message(
        conversation_id,
        "user",
        "Why are the leaves yellow?",
        database_path=database_path,
    )
    save_message(
        conversation_id,
        "assistant",
        "One possible cause is excess moisture.",
        database_path=database_path,
    )

    messages = get_conversation_messages(conversation_id, database_path=database_path)
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "Why are the leaves yellow?"
    assert messages[1]["content"] == "One possible cause is excess moisture."
    assert all(message["created_at"] for message in messages)


def test_new_conversation_does_not_share_messages_with_previous_chat(tmp_path) -> None:
    database_path = tmp_path / "potwise.db"

    first = create_conversation("rose", "Rose", database_path=database_path)
    save_message(first, "user", "Why are my leaves yellow?", database_path=database_path)
    save_message(first, "assistant", "One possible cause is excess moisture.", database_path=database_path)

    second = create_conversation("rose", "Rose", database_path=database_path)
    assert get_conversation_messages(second, database_path=database_path) == []

    save_message(second, "user", "Hello", database_path=database_path)

    assert [message["content"] for message in get_conversation_messages(first, database_path=database_path)] == [
        "Why are my leaves yellow?",
        "One possible cause is excess moisture.",
    ]
    assert [message["content"] for message in get_conversation_messages(second, database_path=database_path)] == [
        "Hello"
    ]


def test_blank_new_chat_can_be_assigned_a_new_plant_without_changing_old_chat(tmp_path) -> None:
    database_path = tmp_path / "potwise.db"

    first = create_conversation("snake_plant", "Snake Plant", database_path=database_path)
    save_message(first, "user", "Why are the leaves curling?", database_path=database_path)
    second = create_conversation(database_path=database_path)

    second_record = get_conversation(second, database_path=database_path)
    assert second_record is not None
    assert second_record["plant_id"] is None
    assert second_record["plant_name"] is None
    assert get_conversation_messages(second, database_path=database_path) == []

    update_conversation(
        second,
        plant_id="rose",
        plant_name="Rose",
        database_path=database_path,
    )

    first_record = get_conversation(first, database_path=database_path)
    assert first_record is not None
    assert first_record["plant_id"] == "snake_plant"
    assert get_conversation_messages(first, database_path=database_path)[0]["content"] == (
        "Why are the leaves curling?"
    )
