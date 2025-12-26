from aiogram.fsm.state import State, StatesGroup

class StoreAdminState(StatesGroup):
    """商店管理状态"""
    waiting_for_price = State()
    waiting_for_stock = State()
    waiting_for_description = State()

class CurrencyAdminState(StatesGroup):
    """精粹管理状态"""
    waiting_for_user = State()  # 如果需要先输入用户
    waiting_for_amount = State()
    waiting_for_reason = State()
