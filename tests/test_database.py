"""
Тесты для database.py
"""

import pytest
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database


@pytest.fixture
def test_db():
    """Создаёт тестовую БД в памяти."""
    original_path = database.DB_PATH
    database.DB_PATH = ":memory:"

    # Переопределяем get_connection для использования памяти
    def get_test_connection():
        return sqlite3.connect(":memory:")

    original_get_conn = database.get_connection
    database.get_connection = get_test_connection

    database.init_db()

    yield database

    database.DB_PATH = original_path
    database.get_connection = original_get_conn


def test_save_ticket(test_db):
    """Тест сохранения тикета."""
    ticket_id = test_db.save_ticket(
        trader_id=123,
        trader_username="test_user",
        trader_name="Test User",
        label="Тестовая категория",
        order_id="ORD-001"
    )

    assert ticket_id == 1
    assert test_db.get_ticket(1) is not None


def test_save_ticket_with_chat_id(test_db):
    """Тест сохранения тикета с trader_chat_id."""
    ticket_id = test_db.save_ticket(
        trader_id=123,
        trader_username="test_user",
        trader_name="Test User",
        label="Тест",
        order_id="ORD-001",
        trader_chat_id=-100123456
    )

    ticket = test_db.get_ticket(ticket_id)
    # trader_chat_id будет в позиции 12 (0-indexed)
    assert ticket is not None


def test_take_ticket(test_db):
    """Тест взятия тикета в работу."""
    ticket_id = test_db.save_ticket(
        trader_id=123,
        trader_username="trader",
        trader_name="Trader",
        label="Test"
    )

    test_db.take_ticket(ticket_id, "support_user", 456)

    ticket = test_db.get_ticket(ticket_id)
    assert ticket[6] == "in_progress"  # status
    assert ticket[7] == "support_user"  # taken_by


def test_close_ticket(test_db):
    """Тест закрытия тикета."""
    ticket_id = test_db.save_ticket(
        trader_id=123,
        trader_username="trader",
        trader_name="Trader",
        label="Test"
    )

    test_db.take_ticket(ticket_id, "support", 456)
    test_db.close_ticket(ticket_id)

    ticket = test_db.get_ticket(ticket_id)
    assert ticket[6] == "closed"


def test_get_open_tickets(test_db):
    """Тест получения открытых тикетов."""
    # Создаём тикеты
    test_db.save_ticket(1, "u1", "U1", "Test1")
    test_db.save_ticket(2, "u2", "U2", "Test2")
    test_db.save_ticket(3, "u3", "U3", "Test3")

    # Закрываем один
    test_db.take_ticket(1, "support", 100)
    test_db.close_ticket(1)

    open_tickets = test_db.get_open_tickets()
    assert len(open_tickets) == 2


def test_get_support_personal_stats(test_db):
    """Тест статистики саппорта."""
    # Создаём и закрываем тикеты
    t1 = test_db.save_ticket(1, "t1", "T1", "Test")
    t2 = test_db.save_ticket(2, "t2", "T2", "Test")
    t3 = test_db.save_ticket(3, "t3", "T3", "Test")

    test_db.take_ticket(t1, "support_user", 100)
    test_db.take_ticket(t2, "support_user", 100)
    test_db.close_ticket(t1)
    test_db.close_ticket(t2)

    stats = test_db.get_support_personal_stats("support_user")

    assert stats["total"] == 2
    assert stats["closed"] == 2
    assert stats["in_progress"] == 0


def test_add_and_get_supports(test_db):
    """Тест добавления и получения саппортов."""
    test_db.add_support(100, "support1", "Support One")
    test_db.add_support(200, "support2", "Support Two")

    supports = test_db.get_all_supports()
    assert len(supports) == 2


def test_get_trader_tickets(test_db):
    """Тест получения тикетов трейдера."""
    trader_id = 12345

    test_db.save_ticket(trader_id, "trader", "Trader", "Test1")
    test_db.save_ticket(trader_id, "trader", "Trader", "Test2")
    test_db.save_ticket(99999, "other", "Other", "Other")

    tickets = test_db.get_trader_tickets(trader_id)
    assert len(tickets) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
