"""
Тесты для database.py с использованием мока Supabase клиента
"""
import pytest
from unittest.mock import MagicMock, patch


# Мок данные
_mock_tickets = []
_mock_supports = []
_mock_next_id = 1


def reset_mocks():
    """Сброс мок данных перед каждым тестом."""
    global _mock_tickets, _mock_supports, _mock_next_id
    _mock_tickets = []
    _mock_supports = []
    _mock_next_id = 1


def create_mock_client():
    """Создать мок Supabase клиент."""
    mock = MagicMock()

    def save_ticket(trader_id, trader_username, trader_name, label, order_id=None, trader_chat_id=None, team_name=None):
        global _mock_next_id
        ticket = {
            "id": _mock_next_id,
            "trader_id": trader_id,
            "trader_username": trader_username,
            "trader_name": trader_name,
            "label": label,
            "order_id": order_id,
            "status": "open",
            "taken_by": None,
            "taken_by_id": None,
            "taken_at": None,
            "closed_at": None,
            "trader_chat_id": trader_chat_id,
            "team_name": team_name,
        }
        _mock_tickets.append(ticket)
        _mock_next_id += 1
        return ticket["id"]

    def take_ticket(ticket_id, support_username, support_id):
        for t in _mock_tickets:
            if t["id"] == ticket_id:
                t["status"] = "in_progress"
                t["taken_by"] = support_username
                t["taken_by_id"] = support_id
                break

    def close_ticket(ticket_id):
        for t in _mock_tickets:
            if t["id"] == ticket_id:
                t["status"] = "closed"
                break

    def get_ticket(ticket_id):
        for t in _mock_tickets:
            if t["id"] == ticket_id:
                return t
        return None

    def get_open_tickets():
        return [t for t in _mock_tickets if t["status"] == "open"]

    def get_all_tickets():
        return _mock_tickets

    def get_trader_tickets(trader_id):
        return [t for t in _mock_tickets if t["trader_id"] == trader_id]

    def get_support_personal_stats(username):
        user_tickets = [t for t in _mock_tickets if t.get("taken_by") == username]
        closed = len([t for t in user_tickets if t["status"] == "closed"])
        in_progress = len([t for t in user_tickets if t["status"] == "in_progress"])
        return {
            "total": len(user_tickets),
            "closed": closed,
            "in_progress": in_progress,
            "avg_seconds": None
        }

    def add_support(tg_id, username, full_name):
        _mock_supports.append({"tg_id": tg_id, "username": username, "full_name": full_name})

    def get_all_supports():
        return _mock_supports

    def get_tickets_summary():
        return {
            "total": len(_mock_tickets),
            "open": len([t for t in _mock_tickets if t["status"] == "open"]),
            "in_progress": len([t for t in _mock_tickets if t["status"] == "in_progress"]),
            "closed": len([t for t in _mock_tickets if t["status"] == "closed"]),
            "today": 0
        }

    def get_label_stats():
        from collections import Counter
        labels = [t["label"] for t in _mock_tickets]
        counts = Counter(labels)
        return list(counts.items())

    def get_support_stats():
        from collections import defaultdict
        stats = defaultdict(lambda: {"total": 0, "closed": 0, "avg_seconds": None})
        for t in _mock_tickets:
            if t.get("taken_by"):
                stats[t["taken_by"]]["total"] += 1
                if t["status"] == "closed":
                    stats[t["taken_by"]]["closed"] += 1
        return [{"username": k, **v} for k, v in stats.items()]

    mock.save_ticket = save_ticket
    mock.take_ticket = take_ticket
    mock.close_ticket = close_ticket
    mock.get_ticket = get_ticket
    mock.get_open_tickets = get_open_tickets
    mock.get_all_tickets = get_all_tickets
    mock.get_trader_tickets = get_trader_tickets
    mock.get_support_personal_stats = get_support_personal_stats
    mock.add_support = add_support
    mock.get_all_supports = get_all_supports
    mock.get_tickets_summary = get_tickets_summary
    mock.get_label_stats = get_label_stats
    mock.get_support_stats = get_support_stats

    return mock


@pytest.fixture(autouse=True)
def reset():
    """Сбрасывает мок данные перед каждым тестом."""
    reset_mocks()
    yield


@pytest.fixture
def db():
    """Мокнутая база данных."""
    import database
    database.USE_SUPABASE = True

    mock_client = create_mock_client()

    # Патчим все функции на мок
    database.save_ticket = mock_client.save_ticket
    database.take_ticket = mock_client.take_ticket
    database.close_ticket = mock_client.close_ticket
    database.get_ticket = mock_client.get_ticket
    database.get_open_tickets = mock_client.get_open_tickets
    database.get_all_tickets = mock_client.get_all_tickets
    database.get_trader_tickets = mock_client.get_trader_tickets
    database.get_support_personal_stats = mock_client.get_support_personal_stats
    database.add_support = mock_client.add_support
    database.get_all_supports = mock_client.get_all_supports
    database.get_tickets_summary = mock_client.get_tickets_summary
    database.get_label_stats = mock_client.get_label_stats
    database.get_support_stats = mock_client.get_support_stats

    return database


def test_save_ticket(db):
    """Тест сохранения тикета."""
    ticket_id = db.save_ticket(
        trader_id=123,
        trader_username="test_user",
        trader_name="Test User",
        label="Тестовая категория",
        order_id="ORD-001"
    )

    assert ticket_id == 1
    assert db.get_ticket(1) is not None


def test_save_ticket_with_chat_id(db):
    """Тест сохранения тикета с trader_chat_id."""
    ticket_id = db.save_ticket(
        trader_id=123,
        trader_username="test_user",
        trader_name="Test User",
        label="Тест",
        order_id="ORD-001",
        trader_chat_id=-100123456
    )

    ticket = db.get_ticket(ticket_id)
    assert ticket is not None
    assert ticket["trader_chat_id"] == -100123456


def test_save_ticket_with_team_name(db):
    """Тест сохранения тикета с team_name (Фаза 2)."""
    ticket_id = db.save_ticket(
        trader_id=123,
        trader_username="trader",
        trader_name="Trader",
        label="Отмена платежа",
        order_id="ORD-001",
        team_name="309 арс"
    )

    ticket = db.get_ticket(ticket_id)
    assert ticket is not None
    assert ticket["team_name"] == "309 арс"


def test_take_ticket(db):
    """Тест взятия тикета в работу."""
    ticket_id = db.save_ticket(
        trader_id=123,
        trader_username="trader",
        trader_name="Trader",
        label="Test"
    )

    db.take_ticket(ticket_id, "support_user", 456)

    ticket = db.get_ticket(ticket_id)
    assert ticket["status"] == "in_progress"
    assert ticket["taken_by"] == "support_user"


def test_close_ticket(db):
    """Тест закрытия тикета."""
    ticket_id = db.save_ticket(
        trader_id=123,
        trader_username="trader",
        trader_name="Trader",
        label="Test"
    )

    db.take_ticket(ticket_id, "support", 456)
    db.close_ticket(ticket_id)

    ticket = db.get_ticket(ticket_id)
    assert ticket["status"] == "closed"


def test_get_open_tickets(db):
    """Тест получения открытых тикетов."""
    db.save_ticket(1, "u1", "U1", "Test1")
    db.save_ticket(2, "u2", "U2", "Test2")
    db.save_ticket(3, "u3", "U3", "Test3")

    db.take_ticket(1, "support", 100)
    db.close_ticket(1)

    open_tickets = db.get_open_tickets()
    assert len(open_tickets) == 2


def test_get_support_personal_stats(db):
    """Тест статистики саппорта."""
    t1 = db.save_ticket(1, "t1", "T1", "Test")
    t2 = db.save_ticket(2, "t2", "T2", "Test")

    db.take_ticket(t1, "support_user", 100)
    db.take_ticket(t2, "support_user", 100)
    db.close_ticket(t1)

    stats = db.get_support_personal_stats("support_user")

    assert stats["total"] == 2
    assert stats["closed"] == 1
    assert stats["in_progress"] == 1


def test_add_and_get_supports(db):
    """Тест добавления и получения саппортов."""
    db.add_support(100, "support1", "Support One")
    db.add_support(200, "support2", "Support Two")

    supports = db.get_all_supports()
    assert len(supports) == 2


def test_get_trader_tickets(db):
    """Тест получения тикетов трейдера."""
    trader_id = 12345

    db.save_ticket(trader_id, "trader", "Trader", "Test1")
    db.save_ticket(trader_id, "trader", "Trader", "Test2")
    db.save_ticket(99999, "other", "Other", "Other")

    tickets = db.get_trader_tickets(trader_id)
    assert len(tickets) == 2


def test_get_tickets_summary(db):
    """Тест получения сводки по тикетам."""
    db.save_ticket(1, "u1", "U1", "Test1")
    db.save_ticket(2, "u2", "U2", "Test2")
    db.save_ticket(3, "u3", "U3", "Test3")

    db.take_ticket(1, "support", 100)
    db.close_ticket(1)

    db.take_ticket(2, "support", 100)

    summary = db.get_tickets_summary()
    assert summary["total"] == 3
    assert summary["closed"] == 1
    assert summary["in_progress"] == 1
    assert summary["open"] == 1


def test_get_label_stats(db):
    """Тест статистики по категориям."""
    db.save_ticket(1, "u1", "U1", "Category A")
    db.save_ticket(2, "u2", "U2", "Category A")
    db.save_ticket(3, "u3", "U3", "Category B")

    stats = db.get_label_stats()
    assert len(stats) == 2

    cat_a = dict(stats)
    assert cat_a.get("Category A") == 2
    assert cat_a.get("Category B") == 1


def test_get_support_stats(db):
    """Тест статистики по всем саппортам."""
    db.save_ticket(1, "t1", "T1", "Test")
    db.save_ticket(2, "t2", "T2", "Test")

    db.take_ticket(1, "support1", 100)
    db.take_ticket(2, "support2", 200)

    stats = db.get_support_stats()
    assert len(stats) == 2

    usernames = {s["username"] for s in stats}
    assert "support1" in usernames
    assert "support2" in usernames


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
