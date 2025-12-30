from aiogram.fsm.state import State, StatesGroup


class StoreAdminState(StatesGroup):
    """商店管理状态"""
    waiting_for_price = State()
    waiting_for_stock = State()
    waiting_for_description = State()

class StoreAddProductState(StatesGroup):
    """添加商品状态"""
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_stock = State()
    waiting_for_description = State()
    waiting_for_category = State()
    waiting_for_action_type = State()


class CurrencyAdminState(StatesGroup):
    """精粹管理状态"""
    waiting_for_user = State()  # 如果需要先输入用户
    waiting_for_amount = State()
    waiting_for_reason = State()


class AdminMainImageState(StatesGroup):
    """主图管理状态"""
    waiting_for_image = State()
    waiting_for_test_input = State()
    waiting_for_schedule_input = State()

class AdminFileState(StatesGroup):
    """文件管理状态

    功能说明:
    - 保存文件等待输入状态
    - 其他操作可按需扩展
    """
    waiting_for_file_input = State()

class QuizAdminState(StatesGroup):
    """问答管理状态"""
    waiting_for_question = State()
    waiting_for_options = State()
    waiting_for_correct_index = State()
    waiting_for_difficulty = State()
    waiting_for_tags = State()
    
    waiting_for_image_tags = State()
