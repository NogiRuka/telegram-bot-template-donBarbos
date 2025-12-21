from __future__ import annotations

import bcrypt


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希

    功能说明:
    - 生成随机盐并使用 bcrypt 算法哈希密码
    - 返回哈希后的字符串

    输入参数:
    - password: 明文密码

    返回值:
    - str: 哈希后的密码字符串
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """验证密码是否匹配哈希

    功能说明:
    - 验证明文密码是否与 bcrypt 哈希匹配

    输入参数:
    - password: 明文密码
    - hashed: 哈希后的密码字符串

    返回值:
    - bool: 是否匹配
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
