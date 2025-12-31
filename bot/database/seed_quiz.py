from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models.quiz import QuizQuestionModel, QuizImageModel, QuizCategoryModel
from datetime import datetime as dt

async def seed_quiz_data(session: AsyncSession) -> None:
    """
    初始化问答数据（如果不存在）
    """
    # 1. 确保分类存在 (ID: 15, Name: LGBT)
    # 用户未明确提供分类名称，这里假设为 "LGBT" (从标签推断)
    category_id = 15
    category_name = "LGBT"
    
    stmt = select(QuizCategoryModel).where(QuizCategoryModel.id == category_id)
    result = await session.execute(stmt)
    category = result.scalar_one_or_none()
    
    if not category:
        category = QuizCategoryModel(
            id=category_id,
            name=category_name,
            sort_order=0,
            is_active=True
        )
        session.add(category)
        await session.flush() # 获取ID，防止后续外键错误
    
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
            difficulty=3,
            reward_base=5,
            reward_bonus=15,
            category_id=category_id,
            tags=["LGBT骄傲月"],
            is_active=True,
            is_deleted=False,
            # created_at=dt(2025, 12, 31, 13, 34, 17),
            # updated_at=dt(2025, 12, 31, 13, 34, 17)
        )
        # 手动设置时间戳需要绕过Mixin的自动设置，或者在add后修改
        # BasicAuditMixin通常使用default=func.now()，但也允许手动赋值
        question.created_at = dt(2025, 12, 31, 13, 34, 17)
        question.updated_at = dt(2025, 12, 31, 13, 34, 17)
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
        image.created_at = dt(2025, 12, 31, 13, 34, 17)
        image.updated_at = dt(2025, 12, 31, 13, 34, 17)
        session.add(image)
        
    await session.commit()
