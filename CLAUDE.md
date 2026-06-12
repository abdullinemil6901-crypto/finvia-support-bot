# Support Bot — Finvia

## Описание

Telegram-бот для саппорт-команды Finvia. Трейдеры пишут боту через `/start`, выбирают категорию, вводят данные → тикет отправляется в саппорт-чат. Саппорты берут и закрывают тикеты через кнопки. Руководство видит статистику и тикеты на дашборде.

**Цель проекта:** Создать AI-агента для автоматизации саппорта. Пока бот собирает тикеты, в будущем планируется подключение к API площадки и внедрение AI-ответов.

---

## Архитектура

```
Telegram bot (aiogram 3.x)
    ├── Polling → handlers (menu + actions)
    ├── FSM → commands_config.py (автогенерация состояний)
    ├── SQLite → database.py (тикеты)
    └── FastAPI → api.py (порт 8000, для дашборда)
                         └── dashboard/index.html (статика)
```

**Ключевое:** Все команды в `commands_config.py` — добавление новой = редактирование ОДНОГО файла.

---

## Структура файлов

| Файл | Назначение |
|------|------------|
| `bot.py` | Точка входа. Запускает polling + API в отдельном потоке |
| `handlers/menu.py` | Команды `/start`, `/my_tickets`, `/stats`, `/export`, управление саппортами |
| `handlers/actions.py` | FSM для тикетов, взятие/закрытие, валидация, retry-логика |
| `commands_config.py` | **Все 13 команд** + автогенерация FSM States |
| `database.py` | SQLite: тикеты, саппорты, расписание |
| `db.py` | SQLite: статистика событий (stats.db) |
| `api.py` | FastAPI: эндпоинты для дашборда |
| `charts.py` | Графики matplotlib (bar, pie, horizontal) |
| `schedule_manager.py` | Работа с schedule.json |
| `keyboards.py` | Inline-клавиатуры (меню, подменю) |
| `config/__init__.py` | Токен, ID чатов, админы |
| `config/menu_config.py` | Категории меню (5 категорий, 13 команд) |
| `dashboard/index.html` | Дашборд (Chart.js, фильтры, пагинация) |

---

## Конфиг (config/__init__.py)

```python
BOT_TOKEN = "..."           # Токен бота
SUPPORT_CHAT_ID = -100...    # Чаг саппортов
TRADER_CHAT_ID = -525...     # Чат трейдеров
ADMIN_IDS = [8480479055]     # ID админов
```

---

## Схема БД (database.py)

### tickets
| Поле | Тип | Описание |
|------|-----|----------|
| id | INTEGER | PK, autoincrement |
| trader_id | INTEGER | Telegram ID трейдера |
| trader_username | TEXT | @username |
| trader_name | TEXT | Полное имя |
| label | TEXT | Тип обращения |
| order_id | TEXT | ID сделки (nullable) |
| status | TEXT | open / in_progress / closed |
| taken_by | TEXT | Username саппорта |
| taken_at | TEXT | ISO timestamp |
| closed_at | TEXT | ISO timestamp |
| created_at | TEXT | ISO timestamp |
| trader_chat_id | INTEGER | Чат трейдера |

### supports
| Поле | Тип |
|------|-----|
| id, tg_id, username, full_name, added_at |

---

## Типы обращений (13 команд)

| Ключ | Label | Нужен Order ID |
|------|-------|----------------|
| apply_cancel_payout | 🚫 Отмена выплаты | Да |
| apply_payout_not_visible | 👁 Выплата не видна на токене | Да |
| apply_extend_time | ⏱ Продлить время ордера | Да |
| apply_no_receipt | 🧾 Нет чека / не прогрузился | Да |
| apply_wrong_receipt | 📎 Неверный чек прикреплён | Да |
| apply_wrong_cvu | ❌ Неверный CVU / не наш реквизит | Да |
| apply_wrong_requisite | 🚷 Не наш реквизит | Да |
| apply_verify_requisites | ⚙️ Верификация реквизитов | Да |
| apply_tech_issue | ⚙️ Технический сбой | Да |
| apply_token_issue | 🔧 Токен не работает | Нет |
| apply_appeal | ⚖️ Апелляция | Да |
| apply_no_traffic | 📡 Нет трафика / ордеров | Нет |
| apply_increase_limits | 📈 Увеличить лимиты | Да |

### Категории меню
- 💸 Выплаты → cancel_payout, payout_not_visible, extend_time
- 🧾 Чеки / документы → no_receipt, wrong_receipt
- ❌ Реквизиты / CVU → wrong_cvu, wrong_requisite, verify_requisites
- ⚙️ Технические проблемы → tech_issue, token_issue, appeal
- 📡 Трафик / лимиты → no_traffic, increase_limits

---

## Жизненный цикл тикета

```
1. Трейдер → /start → выбирает категорию
2. Трейдер → вводит Order ID или описание
3. handlers/actions.py → _send_to_support():
   - Валидация
   - save_ticket() → БД
   - send_with_retry() → в саппорт-чат
   - Кнопки "Взял в работу" / "Завершил"
4. Саппорт → клик "Взял в работу":
   - take_ticket() → БД
   - Уведомление в чат трейдеров
5. Саппорт → клик "Завершил":
   - close_ticket() → БД
   - Уведомление в чат трейдеров
```

---

## API эндпоинты (api.py)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/tickets` | Все тикеты (пагинация, фильтры) |
| GET | `/api/tickets/open` | Открытые тикеты |
| GET | `/api/tickets/{id}` | Один тикет |
| GET | `/api/stats` | Статистика по саппортам |
| GET | `/api/stats/{username}` | Личная статистика |
| GET | `/api/commands` | Команды с количеством тикетов |
| GET | `/api/duty` | Текущий дежурный |
| POST | `/api/duty` | Назначить дежурного |
| GET | `/api/summary` | Сводка (кэш 30 сек) |
| GET | `/health` | Healthcheck |

---

## Известные проблемы (Known Issues)

### Дашборд ✅ Переписан

- Дашборд полностью переписан (2026-06-12)
- Минимализм, быстрая загрузка
- Нужен Realtime или WebSocket для обновлений без перезагрузки

### Бот

- **MemoryStorage** — теряет FSM-состояния при рестарте бота
- **Нет авторизации API** — любой может читать данные
- **SQLite** — не для продакшена под нагрузкой

### Тесты

- **Нет тестов** — нужно добавить pytest

---

## Последние изменения

### 2026-06-12 — Полная переработка дашборда

- **Новый дашборд** — минималистичный дизайн, ~400 строк вместо 1400
- 2 графика: категории (donut) + дни (bar)
- Быстрый поиск с debounce (300ms)
- Один запрос при загрузке (summary + tickets)
- Нет setInterval — не спамит сервер
- Фильтрация по статусу кликом на карточки
- Пагинация локальная (загружаем 100 тикетов)

---

## Правила работы

### НЕ делать
- ❌ `git add -A` — только конкретные файлы
- ❌ Коммиты без описания
- ❌ Хардкодить ID чатов — всегда из config
- ❌ Добавлять функционал сверх задачи

### После каждой задачи
1. Обновить CLAUDE.md (изменения, known issues)
2. Проверить что ничего не сломалось
3. Зафиксировать что сработало / не сработало

### Перед началом задачи
1. Прочитать CLAUDE.md
2. Понять текущее состояние
3. Спланировать минимум изменений

---

## Зависимости

```
aiogram>=3.0
matplotlib
pytz
fastapi
uvicorn[standard]
pydantic
```

---

## Запуск

```bash
cd support_bot
pip install -r requirements.txt
python bot.py
```

API доступно на `http://localhost:8000`
Дашборд: `/dashboard`

---

*Обновлено: 2026-06-12*