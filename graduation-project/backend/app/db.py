# -*- coding: utf-8 -*-
"""数据库连接与会话管理。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {}
pool_kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite 在多线程/并发测试下需要放开线程检查。
    # 连接池必须放大，否则 200 并发压测时会因队列池耗尽而大面积超时；
    # 同时把等待时间调小，让排队请求尽快失败而不是堆积 30 秒。
    connect_args = {"check_same_thread": False, "timeout": 30}
    pool_kwargs = {"pool_size": 40, "max_overflow": 40, "pool_timeout": 10}

engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
    **pool_kwargs,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db():
    """FastAPI 依赖：每个请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  确保模型已注册

    Base.metadata.create_all(bind=engine)
