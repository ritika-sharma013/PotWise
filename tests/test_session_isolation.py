from core.chat_history import (
    create_conversation,
    get_conversation_messages,
    list_recent_conversations,
    save_message,
)
from core.pots import list_saved_pots, save_pot


def test_chat_history_is_isolated_by_database_path(tmp_path) -> None:
    database_a = tmp_path / "session-a.sqlite3"
    database_b = tmp_path / "session-b.sqlite3"

    conversation_a = create_conversation("rose", "Rose", database_path=database_a)
    save_message(conversation_a, "user", "A's message", database_path=database_a)
    conversation_b = create_conversation("aloe_vera", "Aloe Vera", database_path=database_b)
    save_message(conversation_b, "user", "B's message", database_path=database_b)

    assert [chat["id"] for chat in list_recent_conversations(database_path=database_a)] == [
        conversation_a
    ]
    assert [chat["id"] for chat in list_recent_conversations(database_path=database_b)] == [
        conversation_b
    ]
    assert [message["content"] for message in get_conversation_messages(
        conversation_b,
        database_path=database_a,
    )] == []


def test_my_pots_are_isolated_by_database_path(tmp_path) -> None:
    database_a = tmp_path / "session-a.sqlite3"
    database_b = tmp_path / "session-b.sqlite3"

    save_pot("snake_plant", "Snake Plant", database_path=database_a)
    save_pot("rose", "Rose", database_path=database_b)

    assert [pot["plant_id"] for pot in list_saved_pots(database_path=database_a)] == [
        "snake_plant"
    ]
    assert [pot["plant_id"] for pot in list_saved_pots(database_path=database_b)] == [
        "rose"
    ]
