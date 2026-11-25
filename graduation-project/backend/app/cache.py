# -*- coding: utf-8 -*-
"""缓存层：Redis Bitmap + Lua 原子扣减。

设计要点：
  1. 座位状态用 Bitmap 存，key = seat:state:{room_id}:{date}:{slot_id}，
     seat_id 直接作为比特偏移，100 个座位仅占 13 字节；
  2. 抢座用 Lua 脚本把"判断空位 + 占位"合成一次原子操作，
     避免并发请求读到中间状态；
  3. 未配置 REDIS_URL 时 cache.available 为 False，
     业务层自动降级为数据库条件更新（乐观锁），系统仍可用。
"""
from __future__ import annotations

from datetime import date
from typing import Optional, Set

from .config import settings

# KEYS[1] = bitmap key, ARGV[1] = seat_id, ARGV[2] = ttl 秒
LUA_ACQUIRE = """
if redis.call('GETBIT', KEYS[1], ARGV[1]) == 1 then
    return 0
end
redis.call('SETBIT', KEYS[1], ARGV[1], 1)
redis.call('EXPIRE', KEYS[1], ARGV[2])
return 1
"""

LUA_RELEASE = """
return redis.call('SETBIT', KEYS[1], ARGV[1], 0)
"""


def seat_key(room_id: int, d: date, slot_id: int) -> str:
    return f"seat:state:{room_id}:{d.isoformat()}:{slot_id}"


class SeatCache:
    """Redis 座位缓存；Redis 不可用时所有方法安全降级。"""

    def __init__(self) -> None:
        self.client = None
        self._acquire_script = None
        self._release_script = None

    # ------------------------------------------------------------------
    def connect(self) -> None:
        if not settings.REDIS_URL:
            print("[cache] 未配置 REDIS_URL，缓存层关闭，使用数据库乐观锁降级")
            return
        try:
            import redis  # 延迟导入，未安装也不影响启动

            self.client = redis.Redis.from_url(
                settings.REDIS_URL, decode_responses=True, socket_timeout=2
            )
            self.client.ping()
            self._acquire_script = self.client.register_script(LUA_ACQUIRE)
            self._release_script = self.client.register_script(LUA_RELEASE)
            print(f"[cache] Redis 已连接：{settings.REDIS_URL}")
        except Exception as exc:  # noqa: BLE001
            self.client = None
            print(f"[cache] Redis 连接失败，降级为数据库锁：{exc}")

    @property
    def available(self) -> bool:
        return self.client is not None

    # ------------------------------------------------------------------
    def acquire(self, room_id: int, d: date, slot_id: int, seat_id: int) -> Optional[bool]:
        """尝试占位。返回 True=抢到，False=已被占，None=缓存不可用。"""
        if not self.available:
            return None
        try:
            result = self._acquire_script(
                keys=[seat_key(room_id, d, slot_id)],
                args=[seat_id, 2 * 24 * 3600],
            )
            return int(result) == 1
        except Exception as exc:  # noqa: BLE001
            print(f"[cache] acquire 异常，降级：{exc}")
            self.client = None
            return None

    def release(self, room_id: int, d: date, slot_id: int, seat_id: int) -> None:
        if not self.available:
            return
        try:
            self._release_script(keys=[seat_key(room_id, d, slot_id)], args=[seat_id])
        except Exception:  # noqa: BLE001
            pass

    def occupied(self, room_id: int, d: date, slot_id: int) -> Set[int]:
        """读出某房间某时段已占的座位 id 集合。"""
        if not self.available:
            return set()
        try:
            raw = self.client.get(seat_key(room_id, d, slot_id))
            if not raw:
                return set()
            return {i for i, ch in enumerate(reversed(raw)) if ch == "1"}
        except Exception:  # noqa: BLE001
            return set()

    def warm_up(self, room_id: int, d: date, slot_id: int, seat_ids: list[int]) -> None:
        """用数据库中的有效预约预热位图，避免缓存与库不一致。"""
        if not self.available or not seat_ids:
            return
        try:
            pipe = self.client.pipeline()
            for sid in seat_ids:
                pipe.setbit(seat_key(room_id, d, slot_id), sid, 1)
            pipe.expire(seat_key(room_id, d, slot_id), 2 * 24 * 3600)
            pipe.execute()
        except Exception:  # noqa: BLE001
            pass


cache = SeatCache()
