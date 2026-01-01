from aiogram.fsm.state import State, StatesGroup

class UserQuizSubmitState(StatesGroup):
    """用户投稿状态"""
    waiting_for_input = State()
