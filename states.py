from aiogram.fsm.state import State, StatesGroup

class CancelPayoutSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class PayoutNotVisibleSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class ExtendTimeSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class NoReceiptSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class WrongReceiptSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class WrongCVUSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class WrongRequisiteSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class VerifyRequisitesSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class TechIssueSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class TokenIssueSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class AppealSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class NoTrafficSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()

class IncreaseLimitsSG(StatesGroup):
    waiting_for_order_id = State()
    waiting_for_comment = State()
