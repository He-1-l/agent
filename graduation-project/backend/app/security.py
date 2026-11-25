# -*- coding: utf-8 -*-
"""认证与密码工具。

全部基于 Python 标准库实现，不引入 PyJWT / bcrypt，减少环境依赖：
  - 密码：PBKDF2-HMAC-SHA256 + 随机盐
  - 令牌：JWT（HS256），手写签发与校验
"""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from .config import settings


# ----------------------------------------------------------------------
# 密码
# ----------------------------------------------------------------------
def hash_password(raw: str) -> str:
    """返回 pbkdf2$迭代次数$盐$摘要 形式的字符串。"""
    salt = os.urandom(16)
    iterations = 120_000
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, iterations)
    return "pbkdf2${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(raw: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = stored.split("$")
        if algo != "pbkdf2":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


# ----------------------------------------------------------------------
# JWT
# ----------------------------------------------------------------------
def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _sign(message: str) -> str:
    mac = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    return _b64url_encode(mac)


def create_token(subject: str, role: str = "student", extra: Optional[Dict[str, Any]] = None) -> str:
    header = {"alg": settings.ALGORITHM, "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + settings.TOKEN_EXPIRE_MINUTES * 60,
    }
    if extra:
        payload.update(extra)
    seg = "{}.{}".format(
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode()),
        _b64url_encode(json.dumps(payload, separators=(",", ":")).encode()),
    )
    return seg + "." + _sign(seg)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """校验并返回载荷；签名错误或已过期返回 None。"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        signing_input = parts[0] + "." + parts[1]
        if not hmac.compare_digest(_sign(signing_input), parts[2]):
            return None
        payload = json.loads(_b64url_decode(parts[1]))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None
