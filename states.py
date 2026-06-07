from aiogram.fsm.state import State, StatesGroup

class CancelPayoutSG(StatesGroup):
    waiting_for_order_id = State()

class PayoutNotVisibleSG(StatesGroup):
    waiting_for_order_id = State()

class ExtendTimeSG(StatesGroup):
    waiting_for_order_id = State()

class NoReceiptSG(StatesGroup):
    waiting_for_order_id = State()

class WrongReceiptSG(StatesGroup):
    waiting_for_order_id = State()

class WrongCVUSG(StatesGroup):
    waiting_for_order_id = State()

class WrongRequisiteSG(StatesGroup):
    waiting_for_order_id = State()

class VerifyRequisitesSG(StatesGroup):
    waiting_for_order_id = State()

class TechIssueSG(StatesGroup):
    waiting_for_order_id = State()

class TokenIssueSG(StatesGroup):
    waiting_for_order_id = State()

class AppealSG(StatesGroup):
    waiting_for_order_id = State()

class NoTrafficSG(StatesGroup):
    waiting_for_order_id = State()

class IncreaseLimitsSG(StatesGroup):
    waiting_for_order_id = State()
