"""
认证API路由
提供登录与用户信息获取接口
"""

from __future__ import annotations
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

router = APIRouter()

# 开发阶段硬编码配置
SECRET_KEY = "dev_secret_key_change_me_in_prod"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1天

# 硬编码用户凭证
HARDCODED_USERNAME = "桜色男孩"
HARDCODED_PASSWORD = "lustfulboy.com"
HARDCODED_EMAIL = "admin@lustfulboy.com"
HARDCODED_USER_ID = 1

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict

class LoginRequest(BaseModel):
    email: str | None = None
    password: str

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

def create_jwt(data: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    # Ensure exp is present
    if "exp" not in payload:
        payload["exp"] = int(time.time()) + ACCESS_TOKEN_EXPIRE_MINUTES * 60

    header_b64 = base64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(payload).encode("utf-8"))

    signature_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signature_input.encode("utf-8"),
        hashlib.sha256
    ).digest()
    signature_b64 = base64url_encode(signature)

    return f"{signature_input}.{signature_b64}"

def verify_jwt(token: str, secret: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts
        signature_input = f"{header_b64}.{payload_b64}"

        expected_signature = hmac.new(
            secret.encode("utf-8"),
            signature_input.encode("utf-8"),
            hashlib.sha256
        ).digest()

        if base64url_encode(expected_signature) != signature_b64:
            return None

        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + "==").decode("utf-8")
        payload = json.loads(payload_json)

        # Check expiration
        if "exp" in payload and payload["exp"] < time.time():
            return None

        return payload
    except Exception:
        return None

@router.post("/auth/login", response_model=Token)
async def login(form_data: LoginRequest):
    """
    用户登录
    """
    input_identifier = form_data.email or ""
    input_password = form_data.password

    # 验证逻辑：用户名或邮箱匹配，且密码正确
    is_username_match = (input_identifier == HARDCODED_USERNAME)
    is_email_match = input_identifier in (HARDCODED_EMAIL, "admin")

    is_valid = (is_username_match or is_email_match) and (input_password == HARDCODED_PASSWORD)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_jwt({"sub": str(HARDCODED_USER_ID)}, SECRET_KEY)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": HARDCODED_USER_ID,
            "email": HARDCODED_EMAIL,
            "username": HARDCODED_USERNAME,
            "first_name": "Admin",
            "last_name": "User",
            "active": True,
            "roles": [{"id": 1, "name": "admin"}],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    }

@router.get("/auth/me")
async def read_users_me(token: Annotated[str, Depends(oauth2_scheme)]):
    payload = verify_jwt(token, SECRET_KEY)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的凭证")

    user_id = payload.get("sub")
    if user_id != str(HARDCODED_USER_ID):
         raise HTTPException(status_code=401, detail="无效的凭证")

    return {
        "id": HARDCODED_USER_ID,
        "email": HARDCODED_EMAIL,
        "username": HARDCODED_USERNAME,
        "first_name": "Admin",
        "last_name": "User",
        "active": True,
        "roles": [{"id": 1, "name": "admin"}],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
