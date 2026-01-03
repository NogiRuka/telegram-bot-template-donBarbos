"""
投稿审核状态定义
"""

from aiogram.fsm.state import State, StatesGroup


class NotificationReviewStates(StatesGroup):
    """投稿审核状态组"""
    waiting_for_review_comment = State()  # 等待审核留言