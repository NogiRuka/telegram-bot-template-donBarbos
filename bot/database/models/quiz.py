from __future__ import annotations

from sqlalchemy import Index, Integer, Text, JSON, ForeignKey, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk

class QuizQuestionModel(Base, BasicAuditMixin):
    """
    题库表
    """
    __tablename__ = "quiz_questions"

    id: Mapped[auto_int_pk]
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="题目描述")
    options: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="选项列表")
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="正确选项的索引")
    difficulty: Mapped[int] = mapped_column(Integer, default=1, comment="难度等级")
    reward_base: Mapped[int] = mapped_column(Integer, default=5, comment="基础奖励(答错/低保)")
    reward_bonus: Mapped[int] = mapped_column(Integer, default=15, comment="额外奖励(答对)")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("quiz_categories.id"), nullable=True, comment="分类ID")
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="标签")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="扩展数据")

    # 索引
    __table_args__ = (
        Index("idx_quiz_questions_diff", "difficulty", "is_active"),
        Index("idx_quiz_questions_active", "is_active"),
    )

    repr_cols = ("id", "question", "difficulty", "is_active")

class QuizImageModel(Base, BasicAuditMixin):
    """
    问答图片表
    """
    __tablename__ = "quiz_images"

    id: Mapped[auto_int_pk]
    file_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="Telegram File ID")
    file_unique_id: Mapped[str] = mapped_column(String(255), nullable=False, comment="Telegram File Unique ID")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("quiz_categories.id"), nullable=True, comment="分类ID")
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="关联标签")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="图片描述/备注")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="扩展数据")

    # 索引
    __table_args__ = (
        Index("idx_quiz_images_active", "is_active"),
    )

    repr_cols = ("id", "tags", "is_active")

class QuizActiveSessionModel(Base, BasicAuditMixin):
    """
    活跃答题会话表
    """
    __tablename__ = "quiz_active_sessions"

    id: Mapped[auto_int_pk]
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, comment="用户ID (单人单会话)")
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="聊天ID")
    message_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="题目消息ID")
    question_id: Mapped[int] = mapped_column(ForeignKey("quiz_questions.id"), nullable=False, comment="题目ID")
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="正确选项缓存")
    expire_at: Mapped[int] = mapped_column(Integer, nullable=False, comment="过期时间戳")
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="扩展数据")
    
    # 关联
    question: Mapped[QuizQuestionModel] = relationship()

    # 索引
    __table_args__ = (
        Index("idx_quiz_sessions_user", "user_id"),
        Index("idx_quiz_sessions_expire", "expire_at"),
    )

    repr_cols = ("user_id", "question_id", "expire_at")

class QuizLogModel(Base, BasicAuditMixin):
    """
    答题记录表
    """
    __tablename__ = "quiz_logs"

    id: Mapped[auto_int_pk]
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="用户ID")
    chat_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="聊天ID")
    question_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="题目ID")
    user_answer: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="用户选择(NULL表示未答/超时)")
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否正确")
    reward_amount: Mapped[int] = mapped_column(Integer, default=0, comment="获得奖励")
    time_taken: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="耗时(ms)")
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="扩展数据")

    # 索引
    __table_args__ = (
        Index("idx_quiz_logs_user", "user_id", "created_at"),
        Index("idx_quiz_logs_question", "question_id"),
        Index("idx_quiz_logs_correct", "is_correct"),
    )

    repr_cols = ("user_id", "question_id", "is_correct", "reward_amount")

class QuizCategoryModel(Base, BasicAuditMixin):
    """
    问答分类表
    """
    __tablename__ = "quiz_categories"

    id: Mapped[auto_int_pk]
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序权重")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    repr_cols = ("id", "name", "sort_order")
