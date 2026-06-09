# Лог разработки Support Bot

> Этот документ ведётся для переноса данных на админ-дашборд.

---

## Текущее состояние проекта

**Репозиторий:** https://github.com/abdullinemil6901-crypto/finvia-support-bot  
**Ветка:** main  
**Последний коммит:** a434d3c

---

## Структура базы данных

### Таблица `tickets`

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER PK | Уникальный ID тикета |
| trader_id | INTEGER | Telegram ID трейдера |
| trader_username | TEXT | Username трейдера |
| trader_name | TEXT | Имя трейдера |
| trader_chat_id | INTEGER | Chat ID трейдера (для уведомлений) |
| label | TEXT | Категория обращения |
| order_id | TEXT | ID ордера (если применимо) |
| status | TEXT | open / taken / closed |
| taken_by | TEXT | Username саппорта, взявшего тикет |
| taken_at | TEXT | Время взятия тикета (ISO) |
| closed_at | TEXT | Время закрытия тикета (ISO) |
| created_at | TEXT | Время создания тикета (ISO) |

### Таблица `duty`

| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER PK | ID записи |
| support_username | TEXT | Username дежурного саппорта |
| set_at | TEXT | Время назначения дежурного |

---

## API функций базы данных

### `save_ticket(trader_id, trader_username, trader_name, label, order_id=None, trader_chat_id=None) -> int`
Создаёт новый тикет. Возвращает ID созданного тикета.

### `get_open_tickets() -> list`
Возвращает все открытые тикеты (status='open'), отсортированные по дате создания (старые первые).

**Поля в ответе:** `id, trader_id, trader_username, trader_name, label, order_id, created_at, trader_chat_id`

### `get_tickets_by_support(support_username: str) -> list`
Возвращает все тикеты конкретного саппорта, отсортированные по убыванию даты создания.

**Поля в ответе:** `id, label, order_id, status, trader_username, trader_name, taken_at, closed_at, created_at`

### `take_ticket(ticket_id, support_username) -> bool`
Помечает тикет как взятый саппортом.

### `close_ticket(ticket_id) -> bool`
Закрывает тикет.

### `get_support_stats() -> list`
Возвращает статистику по всем саппортам.

**Поля в ответе:** `support_username, total, closed, in_progress, avg_seconds`

### `get_support_personal_stats(support_username: str) -> dict`
Возвращает личную статистику конкретного саппорта.

**Поля в ответе:** `total, closed, in_progress, avg_seconds`

### `get_duty() -> str | None`
Возвращает username текущего дежурного саппорта.

### `set_duty(support_username: str)`
Назначает дежурного саппорта.

---

## Категории обращений (label)

| Код | Описание |
|-----|----------|
| appeal | Апелляция |
| payment_issue | Проблема с оплатой |
| order_cancel | Отмена ордера |
| account_block | Блокировка аккаунта |
| verification | Верификация |
| withdrawal | Вывод средств |
| deposit | Пополнение |
| trade_dispute | Торговый спор |
| technical | Техническая проблема |
| other | Другое |

---

## Лог изменений

### Коммит a434d3c (2026-06-08)
**Изменения:**
- `database.py`: добавлен параметр `trader_chat_id` в `save_ticket()`
- `database.py`: добавлена функция `get_open_tickets()`
- `database.py`: добавлена функция `get_tickets_by_support()`
- `PROJECT_PLAN.md`: добавлен лог прогресса сессии разработки

### Коммит 6dddbb6
- Добавлен алиас `TRADER_CHAT_ID` в config

### Коммит fdf616a
- Добавлена поддержка `trader_chat_id` и мульти-чат архитектура

### Коммит f15f569
- Добавлены FSM-хендлеры для 13 типов тикетов с уведомлениями саппорта/трейдера

---

## Что нужно для дашборда

### Эндпоинты (будущий REST API)

```
GET  /api/tickets?status=open          → get_open_tickets()
GET  /api/tickets?support=username     → get_tickets_by_support(username)
GET  /api/stats                        → get_support_stats()
GET  /api/stats/:username              → get_support_personal_stats(username)
GET  /api/duty                         → get_duty()
POST /api/duty                         → set_duty(username)
```

### Виджеты дашборда

1. **Открытые тикеты** — таблица с колонками: ID, трейдер, категория, ордер, время создания
2. **Статистика саппортов** — таблица: саппорт, всего, закрыто, в работе, среднее время
3. **Текущий дежурный** — имя дежурного + кнопка смены
4. **График по времени** — количество тикетов по дням/часам
5. **Распределение по категориям** — pie chart по label

---

## Следующие шаги

- [ ] Создать REST API (FastAPI или Flask) поверх database.py
- [ ] Подключить дашборд к API
- [ ] Добавить авторизацию для дашборда
- [ ] Перейти с SQLite на PostgreSQL для продакшена
- [ ] Добавить логирование ошибок
