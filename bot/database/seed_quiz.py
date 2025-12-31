from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models.quiz import QuizQuestionModel, QuizImageModel, QuizCategoryModel

async def seed_quiz_data(session: AsyncSession) -> None:
    """
    初始化问答数据（如果不存在）
    """
    # 1. 确保分类存在 (ID: 15)
    category_id = 15
    # config_service.py 已初始化分类 1-15，此处无需重复创建，
    # 仅需确认 ID 15 存在即可（通常对应"其他"或用户自定义）
    # 如果不存在（例如 config_service 未运行），则按需创建
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.id == category_id)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        # 仅在不存在时创建，避免冲突
        category = QuizCategoryModel(
            id=category_id,
            name="其他",
            sort_order=0,
            is_active=True
        )
        session.add(category)
        await session.flush() # 获取ID
    
    # 2. 插入题目
    question_id = 1
    stmt = select(QuizQuestionModel).where(QuizQuestionModel.id == question_id)
    result = await session.execute(stmt)
    question = result.scalar_one_or_none()
    
    if not question:
        question = QuizQuestionModel(
            id=question_id,
            question="LGBT骄傲月是什么时候？",
            options=["3月", "6月", "9月", "12月"],
            correct_index=1,
            difficulty=1,
            reward_base=5,
            reward_bonus=15,
            category_id=category_id,
            tags=["LGBT骄傲月"],
            is_active=False,
            is_deleted=False,
        )
        session.add(question)
    
    # 3. 插入题图
    image_id = 1
    stmt = select(QuizImageModel).where(QuizImageModel.id == image_id)
    result = await session.execute(stmt)
    image = result.scalar_one_or_none()
    
    if not image:
        image = QuizImageModel(
            id=image_id,
            file_id="AgACAgUAAxkBAAIQPWlUrh7rd0L2GkVY51cwj7YnpE_vAAIqC2sbObWpVqjVWcXRhKnkAQADAgADeQADOAQ",
            file_unique_id="AQADKgtrGzm1qVZ-",
            category_id=category_id,
            tags=["LGBT骄傲月"],
            description="自动添加于题目 1",
            image_source="https://zh.wikipedia.org/zh-cn/%E5%90%8C%E5%BF%97%E9%AA%84%E5%82%B2#/media/File:Oslo_Pride_Parade_35.jpg",
            extra_caption="2018年奥斯陆骄傲游行",
            is_active=True,
            is_deleted=False,
        )
        session.add(image)
        
    await session.commit()
