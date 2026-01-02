from typing import TypedDict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.database.models import QuizCategoryModel

class ParsedQuiz(TypedDict):
    question: str
    options: list[str]
    correct_index: int
    category_id: int
    category_name: str
    tags: list[str]
    difficulty: int
    image_source: Optional[str]
    extra_caption: Optional[str]

class QuizParseError(Exception):
    pass

async def parse_quiz_input(session: AsyncSession, text: str) -> ParsedQuiz:
    """
    解析题目输入文本
    
    格式:
    第1行：题目描述
    第2行：选项A　选项B　选项C　选项D（空格分隔）
    第3行：正确答案序号（1-4）
    第4行：分类ID
    第5行：标签1　标签2（空格或逗号分隔）
    第6行：难度系数（1-5，可选，默认1）
    第7行：图片来源（可选）
    第8行：图片补充说明（可选）
    """
    if not text:
        raise QuizParseError("请输入题目内容。")

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 至少需要前5行 (题目, 选项, 答案, 分类, 标签)
    if len(lines) < 5:
        raise QuizParseError(
            "格式错误，行数不足。\n"
            "请确保至少包含：题目、选项、答案序号、分类、标签。"
        )

    # 1. 题目
    question_text = lines[0]

    # 2. 选项
    options_text = lines[1]
    options = [o for o in options_text.replace("　", " ").split(" ") if o]
    if len(options) != 4:
        raise QuizParseError(f"选项解析失败，找到 {len(options)} 个选项，需要 4 个。")

    # 3. 答案
    correct_idx_raw = lines[2]
    if not correct_idx_raw.isdigit() or not (1 <= int(correct_idx_raw) <= 4):
        raise QuizParseError("正确答案序号必须是 1-4 的数字。")
    correct_index = int(correct_idx_raw) - 1

    # 4. 分类
    category_input = lines[3]
    category_id = None
    category_name = "未知"
    if category_input.isdigit():
        cat_id = int(category_input)
        stmt = select(QuizCategoryModel).where(QuizCategoryModel.id == cat_id, QuizCategoryModel.is_deleted == False)
        result = await session.execute(stmt)
        cat = result.scalar_one_or_none()
        if cat:
            category_id = cat.id
            category_name = cat.name
        else:
            raise QuizParseError(f"未找到ID为 {cat_id} 的分类。")
    else:
        raise QuizParseError("分类必须填写ID（数字）。")

    # 5. 标签 (必填)
    tags_line = lines[4].strip()
    tags = []

    # 统一中文逗号
    tags_line = tags_line.replace("，", ",")

    if "," in tags_line:
        # 有逗号，按逗号分隔，保留空格
        tags = [t.strip() for t in tags_line.split(",") if t.strip()]
    else:
        # 无逗号，按空格分隔（支持全角/半角空格）
        tags_line = tags_line.replace("　", " ")
        tags = [t.strip() for t in tags_line.split() if t.strip()]

    if not tags:
         raise QuizParseError("标签不能为空。")

    # 6. 难度 (可选)
    difficulty = 1
    if len(lines) > 5 and lines[5].isdigit():
        diff_val = int(lines[5])
        if 1 <= diff_val <= 5:
            difficulty = diff_val

    # 7. 图片来源 (可选)
    image_source = None
    if len(lines) > 6:
        image_source = lines[6]

    # 8. 图片补充说明 (可选)
    extra_caption = None
    if len(lines) > 7:
        extra_caption = lines[7]

    return {
        "question": question_text,
        "options": options,
        "correct_index": correct_index,
        "category_id": category_id,
        "category_name": category_name,
        "tags": tags,
        "difficulty": difficulty,
        "image_source": image_source,
        "extra_caption": extra_caption
    }
