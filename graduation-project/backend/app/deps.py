# -*- coding: utf-8 -*-
"""FastAPI 依赖：从请求头解析并校验 JWT。"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .models import Admin, Student
from .security import decode_token


def _extract_token(authorization: Optional[str], token: Optional[str]) -> str:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if token:
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="缺少访问令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_student(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Student:
    payload = decode_token(_extract_token(authorization, token))
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    student = db.get(Student, int(payload["sub"])) if payload.get("role") == "student" else None
    if not student or student.status != 1:
        raise HTTPException(status_code=401, detail="账号不存在或已禁用")
    return student


def get_current_admin(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Admin:
    payload = decode_token(_extract_token(authorization, token))
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="需要管理员权限")
    admin = db.get(Admin, int(payload["sub"]))
    if not admin or admin.status != 1:
        raise HTTPException(status_code=401, detail="管理员不存在或已禁用")
    return admin


def lock_mode(x_lock_mode: Optional[str] = Header(default=None)) -> str:
    """压测对照实验用：通过请求头切换加锁策略。

    默认 auto：缓存可用走 Redis，否则走数据库唯一索引。
    """
    if x_lock_mode in ("db", "redis", "auto"):
        return x_lock_mode
    return "auto"
