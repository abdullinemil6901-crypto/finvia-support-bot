"""
Support Bot — FSM States
Импортирует сгенерированные StateGroup из commands_config.py
для обратной совместимости с существующим кодом.
"""

from commands_config import (
    CancelPayoutSG, PayoutNotVisibleSG, ExtendTimeSG,
    NoReceiptSG, WrongReceiptSG, WrongCVUSG, WrongRequisiteSG,
    VerifyRequisitesSG, TechIssueSG, TokenIssueSG, AppealSG,
    NoTrafficSG, IncreaseLimitsSG,
    ALL_STATE_CLASSES
)

__all__ = [
    "CancelPayoutSG", "PayoutNotVisibleSG", "ExtendTimeSG",
    "NoReceiptSG", "WrongReceiptSG", "WrongCVUSG", "WrongRequisiteSG",
    "VerifyRequisitesSG", "TechIssueSG", "TokenIssueSG", "AppealSG",
    "NoTrafficSG", "IncreaseLimitsSG",
    "ALL_STATE_CLASSES"
]
