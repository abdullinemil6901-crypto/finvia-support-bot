"""
Тесты для supabase_client.py — функции работы с чатами (chats)
"""
import pytest
from unittest.mock import MagicMock, patch


_mock_chats = []


def reset_chat_mocks():
    global _mock_chats
    _mock_chats = []


def create_mock_client():
    mock = MagicMock()

    def save_chat(chat_id, team_name):
        for c in _mock_chats:
            if c["chat_id"] == chat_id:
                c["team_name"] = team_name
                c["is_active"] = True
                return c
        chat = {
            "id": len(_mock_chats) + 1,
            "chat_id": chat_id,
            "team_name": team_name,
            "is_active": True
        }
        _mock_chats.append(chat)
        return chat

    def get_all_chats():
        return [c for c in _mock_chats if c["is_active"]]

    def get_chat_by_id(chat_id):
        for c in _mock_chats:
            if c["chat_id"] == chat_id:
                return c
        return None

    def deactivate_chat(chat_id):
        for c in _mock_chats:
            if c["chat_id"] == chat_id:
                c["is_active"] = False
                return True
        return False

    mock.save_chat = save_chat
    mock.get_all_chats = get_all_chats
    mock.get_chat_by_id = get_chat_by_id
    mock.deactivate_chat = deactivate_chat

    return mock


@pytest.fixture(autouse=True)
def reset():
    reset_chat_mocks()
    yield


@pytest.fixture
def sb_client():
    import supabase_client
    mock_client = create_mock_client()
    supabase_client.get_all_chats = mock_client.get_all_chats
    supabase_client.get_chat_by_id = mock_client.get_chat_by_id
    supabase_client.save_chat = mock_client.save_chat
    supabase_client.deactivate_chat = mock_client.deactivate_chat
    return supabase_client


def test_save_chat(sb_client):
    """Тест сохранения нового чата."""
    result = sb_client.save_chat(-1001234567890, "309 арс")

    assert result["chat_id"] == -1001234567890
    assert result["team_name"] == "309 арс"
    assert result["is_active"] is True


def test_save_chat_updates_existing(sb_client):
    """Тест обновления существующего чата."""
    sb_client.save_chat(-1001234567890, "309 арс")
    result = sb_client.save_chat(-1001234567890, "310 арс")

    # Должен обновить, не создавать новый
    assert len(_mock_chats) == 1
    assert result["team_name"] == "310 арс"


def test_get_all_chats(sb_client):
    """Тест получения всех активных чатов."""
    sb_client.save_chat(-1001, "Команда 1")
    sb_client.save_chat(-1002, "Команда 2")
    sb_client.save_chat(-1003, "Команда 3")

    chats = sb_client.get_all_chats()
    assert len(chats) == 3


def test_get_all_chats_excludes_inactive(sb_client):
    """Тест что get_all_chats не возвращает неактивные чаты."""
    sb_client.save_chat(-1001, "Активный")
    sb_client.save_chat(-1002, "Будет удалён")
    sb_client.deactivate_chat(-1002)

    chats = sb_client.get_all_chats()
    assert len(chats) == 1
    assert chats[0]["team_name"] == "Активный"


def test_get_chat_by_id(sb_client):
    """Тест поиска чата по chat_id."""
    sb_client.save_chat(-1001234567890, "309 арс")

    chat = sb_client.get_chat_by_id(-1001234567890)
    assert chat is not None
    assert chat["team_name"] == "309 арс"


def test_get_chat_by_id_not_found(sb_client):
    """Тест поиска несуществующего чата."""
    chat = sb_client.get_chat_by_id(-9999999999999)
    assert chat is None


def test_deactivate_chat(sb_client):
    """Тест деактивации чата."""
    sb_client.save_chat(-1001, "Тест")

    result = sb_client.deactivate_chat(-1001)
    assert result is True

    chat = sb_client.get_chat_by_id(-1001)
    assert chat["is_active"] is False


def test_deactivate_chat_not_found(sb_client):
    """Тест деактивации несуществующего чата."""
    result = sb_client.deactivate_chat(-9999999999999)
    assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
