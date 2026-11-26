# -*- coding: utf-8 -*-
"""统一时间工具：所有业务时间都用北京时间。

为什么需要这个模块：
    服务器（Linux / PythonAnywhere / 云主机）的系统时区通常是 UTC，
    datetime.now() 拿到的是 UTC 时间，比北京时间慢 8 小时。

    如果直接用它做业务判断，会出现两个错：
      1) 下午 15:00 能预约当天 08:00-10:00 的时段（服务器以为才 07:00，时段还没开始）
      2) 北京时间凌晨 0-8 点，date.today() 会返回"昨天"，导致"约明天"被拒

    所以业务代码里一律用 now_bj() / today_bj()，不要直接用 datetime.now() / date.today()。

实现方式：
    用固定 UTC+8 偏移，不依赖系统时区数据库（tzdata 缺失时会报
    "No time zone found with key Asia/Shanghai"）。中国不实行夏令时，
    固定偏移永远正确。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# 北京时间 = UTC+8（中国无夏令时，固定偏移即正确）
BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def now_bj() -> datetime:
    """当前北京时间（不带时区信息的 naive datetime，可直接与数据库字段比较）。"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


def today_bj() -> date:
    """当前北京时间的日期。"""
    return now_bj().date()
