from aiogram import Router
from aiogram.fsm.state import State, StatesGroup

router = Router(name="notification")

class NotificationStates(StatesGroup):
    """通知相关状态"""
    waiting_for_additional_sender = State()  # 等待输入额外通知者
