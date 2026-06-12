"""
Support Bot — FSM States
Импортирует сгенерированные StateGroup из commands_config.py
для обратной совместимости с существующим кодом.
"""

from commands_config import ALL_STATE_CLASSES

# Экспортируем для обратной совместимости
__all__ = ["ALL_STATE_CLASSES"]
