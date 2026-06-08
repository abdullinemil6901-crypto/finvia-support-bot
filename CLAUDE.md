# Support Bot — Project Memory (CLAUDE.md)

## Project Overview
Telegram support bot for traders. Built with **aiogram 3.x**, Python, SQLite.

## Repository Structure
```
support_bot/
├── bot.py                  # Entry point, bot/dispatcher init
├── config.py               # All constants: SUPPORT_CHAT_ID, TOKEN, etc.
├── database.py             # SQLite: save_ticket, take_ticket, close_ticket, get_ticket
├── states.py               # FSMContext state groups (one per issue type)
├── keyboards.py            # build_main_menu, build_ticket_keyboard
└── handlers/
    ├── actions.py          # All callback + message handlers
    └── __init__.py
```

## Key Architectural Decisions
- **Single router** in `handlers/actions.py` — all handlers registered here
- **FSM per issue type** — each support category has its own StateGroup
- **`needs_order_id` flag** — determines whether bot asks for Order ID or free-text description
- **`APPLY_HANDLERS` dict** — maps callback_data → (StateGroup, label, needs_order_id)
- **`_send_to_support`** — single shared handler for all FSM states, registered via loop at bottom of file
- **`SUPPORT_CHAT_ID`** — always imported from `config`, never hardcoded

## Supported Issue Types (13 total)
| callback_data | Label | Needs Order ID |
|---|---|---|
| apply_cancel_payout | Отмена выплаты | Yes |
| apply_payout_not_visible | Выплата не отображается | Yes |
| apply_extend_time | Продление времени | Yes |
| apply_no_receipt | Нет чека | Yes |
| apply_wrong_receipt | Неверный чек | Yes |
| apply_wrong_cvu | Неверный CVU | Yes |
| apply_wrong_requisite | Не наш реквизит | Yes |
| apply_verify_requisites | Верификация реквизитов | Yes |
| apply_tech_issue | Технический сбой | Yes |
| apply_token_issue | Токен не работает | No |
| apply_appeal | Апелляция | Yes |
| apply_no_traffic | Нет трафика / ордеров | No |
| apply_increase_limits | Увеличить лимиты | Yes |

## Ticket Lifecycle
1. Trader clicks button → `apply_start` → FSM state set
2. Trader sends Order ID or description → `_send_to_support`
3. `save_ticket()` → ticket saved to DB, sent to `SUPPORT_CHAT_ID` with inline keyboard
4. Support clicks "Взять" → `handle_take_ticket` → trader notified, button changes to "Завершил"
5. Support clicks "Завершил" → `handle_close_ticket` → trader notified, ticket closed in DB

## Trader Notifications
- On **take**: bot sends message that request is being handled
- On **close**: bot sends message that request is resolved
- Notifications wrapped in `try/except` — bot continues if trader blocked bot

## Logging
- `logger = logging.getLogger(__name__)` in every handler file
- Log ticket take: `logger.info("Ticket %s taken by %s (id=%s)", ticket_id, username, id)`

## Config (config.py) — Required Variables
```python
SUPPORT_CHAT_ID: int   # Telegram chat ID for support team
BOT_TOKEN: str         # Bot token from @BotFather
```

## Database Schema (database.py)
Functions used:
- `save_ticket(trader_id, trader_username, trader_name, label, order_id)` → returns `ticket_id`
- `take_ticket(ticket_id, support_username, support_id)`
- `close_ticket(ticket_id)`
- `get_ticket(ticket_id)` → returns tuple; `ticket[1]` = `trader_id`

## Important Rules
- **NEVER hardcode** `SUPPORT_CHAT_ID` — always use `from config import SUPPORT_CHAT_ID`
- **NEVER use** `git add -A` — stage files explicitly
- **NEVER commit** unless user explicitly asks
- When adding a new issue type: add StateGroup to `states.py`, add entry to `APPLY_HANDLERS`, register in the loop at bottom of `actions.py`

## Recent Changes
- Removed hardcoded `SUPPORT_CHAT_ID`, now imported from `config`
- Added `logging` to `actions.py`
- Added trader notification when ticket is taken (`handle_take_ticket`)
