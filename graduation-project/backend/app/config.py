# -*- coding: utf-8 -*-
"""全局配置：全部通过环境变量覆盖，默认值保证零配置可跑。"""
import os


class Settings:
    APP_NAME = "高校自习室座位预约系统"
    VERSION = "1.0.0"

    # 安全相关
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-please")
    ALGORITHM = "HS256"
    TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "1440"))

    # 数据库：默认 SQLite，配 MySQL 时改成
    # mysql+pymysql://user:pass@127.0.0.1:3306/study_room?charset=utf8mb4
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./studyroom.db")

    # Redis：留空则不启用缓存层，系统自动降级为数据库乐观锁
    REDIS_URL = os.getenv("REDIS_URL", "")

    # 业务规则
    CHECKIN_GRACE_MINUTES = int(os.getenv("CHECKIN_GRACE_MINUTES", "15"))
    MAX_RESERVE_PER_DAY = int(os.getenv("MAX_RESERVE_PER_DAY", "3"))
    MIN_CREDIT_TO_RESERVE = int(os.getenv("MIN_CREDIT_TO_RESERVE", "80"))
    CANCEL_PENALTY = int(os.getenv("CANCEL_PENALTY", "0"))
    NO_SHOW_PENALTY = int(os.getenv("NO_SHOW_PENALTY", "5"))

    # 时段开始后仍允许预约（抢被释放的座位），但距结束不足这么多分钟就不让约了，
    # 否则刚约上就要到点，没有实际意义。
    MIN_REMAINING_MINUTES = int(os.getenv("MIN_REMAINING_MINUTES", "30"))

    # 压测对照实验开关：开启后可通过请求头 X-Lock-Mode 切换加锁策略
    ENABLE_BENCH_MODE = os.getenv("ENABLE_BENCH_MODE", "1") == "1"


settings = Settings()
