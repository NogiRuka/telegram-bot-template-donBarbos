from aiogram.fsm.state import State, StatesGroup


class UserQuizSubmitState(StatesGroup):
    """用户投稿状态"""
    waiting_for_input = State()

class UserRequestState(StatesGroup):
    """用户求片状态"""
    waiting_for_input = State()

class UserSubmitState(StatesGroup):
    """用户投稿状态"""
    waiting_for_input = State()

class UserSubmissionState(StatesGroup):
    """用户求片/投稿中心状态"""


class RedPacketWizardStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_amount = State()
    waiting_for_count = State()
    waiting_for_target = State()
    waiting_for_message = State()
