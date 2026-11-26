# -*- coding: utf-8 -*-
"""并发对照实验脚本 —— 用来验证三层防超卖的实际效果。

三种模式：
  nolock  无任何保护（独立 SQLite 表，不建唯一索引），用来复现超卖现象
  db      只靠数据库唯一索引（HTTP 请求头 X-Lock-Mode: db）
  redis   缓存原子扣减 + 唯一索引兜底（X-Lock-Mode: redis）

用法：
  # 对照组：本地跑，不需要启动服务
  python -m scripts.benchmark --mode nolock --concurrency 200 --seats 100

  # 实验组：先启动 uvicorn，再跑
  python -m scripts.benchmark --mode db    --url http://127.0.0.1:8000 --users 200 --seats 100
  python -m scripts.benchmark --mode redis --url http://127.0.0.1:8000 --users 200 --seats 100
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Tuple

DEFAULT_PASSWORD = "123456"

# 北京时间固定 UTC+8，压测的"今天"也按北京时间算
_BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def _today_bj() -> date:
    return datetime.now(_BEIJING_TZ).date()


# ----------------------------------------------------------------------
# 工具
# ----------------------------------------------------------------------
def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    data = sorted(values)
    k = max(0, min(len(data) - 1, int(round((p / 100.0) * (len(data) - 1)))))
    return data[k]


def post_json(url: str, payload: dict, token: str | None = None,
              headers: Dict[str, str] | None = None, timeout: int = 30) -> Tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "ignore")
        try:
            return exc.code, json.loads(raw)
        except Exception:  # noqa: BLE001
            return exc.code, {"detail": raw[:200]}
    except Exception as exc:  # noqa: BLE001
        return 0, {"detail": str(exc)}


def get_json(url: str, token: str | None = None, timeout: int = 30) -> Tuple[int, dict]:
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception:  # noqa: BLE001
        return 0, {}


# ----------------------------------------------------------------------
# 对照组：无唯一约束的写入路径
# ----------------------------------------------------------------------
def run_nolock(concurrency: int, seats: int, window_ms: float = 2.0) -> dict:
    db_path = os.path.join(tempfile.gettempdir(), "bench_nolock.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE nolock (seat_id INTEGER, created REAL)")
    conn.commit()
    conn.close()

    local = threading.local()
    lock = threading.Lock()
    inserted: List[int] = []
    opened: List[sqlite3.Connection] = []

    def connect() -> sqlite3.Connection:
        if not hasattr(local, "conn"):
            c = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=30000")
            local.conn = c
            with lock:
                opened.append(c)
        return local.conn

    def worker(seat_id: int) -> None:
        conn_ = connect()
        cur = conn_.execute(
            "SELECT COUNT(*) FROM nolock WHERE seat_id = ?", (seat_id,)
        )
        if cur.fetchone()[0] == 0:          # 先查
            time.sleep(window_ms / 1000.0)  # 业务处理窗口，竞态就发生在这里
            conn_.execute(
                "INSERT INTO nolock (seat_id, created) VALUES (?, ?)",
                (seat_id, time.time()),
            )
            conn_.commit()                  # 再写
            with lock:
                inserted.append(seat_id)

    seat_ids = [(i % seats) + 1 for i in range(concurrency)]
    start = time.perf_counter()
    barrier = threading.Barrier(min(concurrency, 200))

    def guarded(seat_id: int) -> None:
        try:
            barrier.wait(timeout=10)
        except Exception:  # noqa: BLE001
            pass
        worker(seat_id)

    spinner = ThreadPoolExecutor(max_workers=min(concurrency, 200))
    list(spinner.map(guarded, seat_ids))
    spinner.shutdown(wait=True)
    elapsed = time.perf_counter() - start

    conn = sqlite3.connect(db_path, timeout=30)
    rows = conn.execute(
        "SELECT seat_id, COUNT(*) c FROM nolock GROUP BY seat_id HAVING c > 1"
    ).fetchall()
    total_rows = conn.execute("SELECT COUNT(*) FROM nolock").fetchone()[0]
    conn.close()

    for c in opened:
        try:
            c.close()
        except Exception:  # noqa: BLE001
            pass
    for suffix in ("", "-wal", "-shm"):
        try:
            os.remove(db_path + suffix)
        except OSError:
            pass

    oversold = sum(c - 1 for _, c in rows)
    return {
        "mode": "nolock",
        "concurrency": concurrency,
        "seats": seats,
        "requests": concurrency,
        "success": total_rows,
        "conflict": concurrency - total_rows,
        "oversold": oversold,
        "duplicated_seats": len(rows),
        "elapsed_sec": round(elapsed, 3),
        "tps": round(total_rows / elapsed, 1) if elapsed > 0 else 0,
        "p50_ms": 0,
        "p95_ms": 0,
        "note": "无唯一索引的写入路径，超卖数 > 0 即证明竞态存在",
    }


# ----------------------------------------------------------------------
# 实验组：走 HTTP 接口
# ----------------------------------------------------------------------
def login_all(base: str, users: int, concurrency: int) -> List[str]:
    tokens: List[str] = []
    lock = threading.Lock()

    def one(i: int) -> None:
        code, data = post_json(f"{base}/api/auth/login", {
            "student_no": f"bench{i:04d}", "password": DEFAULT_PASSWORD,
        })
        if code == 200 and data.get("access_token"):
            with lock:
                tokens.append(data["access_token"])

    with ThreadPoolExecutor(max_workers=min(concurrency, 50)) as pool:
        list(pool.map(one, range(1, users + 1)))
    return tokens


def run_http(base: str, mode: str, users: int, seats: int,
             concurrency: int, room_id: int, slot_id: int) -> dict:
    print(f"[bench] 登录 {users} 个账号 ...")
    tokens = login_all(base, users, concurrency)
    if not tokens:
        raise SystemExit("登录失败：请先执行 python -m scripts.init_db 生成压测账号")

    code, health = get_json(f"{base}/api/health")
    seat_map: List[int] = []
    code, data = get_json(
        f"{base}/api/rooms/{room_id}/seats?reserve_date={_today_bj().isoformat()}"
        f"&slot_id={slot_id}", token=tokens[0])
    if code == 200:
        seat_map = [s["id"] for s in data.get("seats", []) if s["state"] != "maintenance"]
    if not seat_map:
        raise SystemExit("未能取到座位列表，请检查房间号与时段")

    targets = (seat_map * ((users // len(seat_map)) + 1))[:users]
    targets = targets[:seats] if len(targets) > seats else targets[:users]
    # 让请求数大于座位数，才能压出超卖场景
    while len(targets) < users:
        targets.append(seat_map[len(targets) % len(seat_map)])

    latencies: List[float] = []
    success = conflict = error = 0
    lock = threading.Lock()
    barrier = threading.Barrier(min(concurrency, 200))

    def one(args: Tuple[str, int]) -> None:
        nonlocal success, conflict, error
        token, seat_id = args
        try:
            barrier.wait(timeout=15)
        except Exception:  # noqa: BLE001
            pass
        t0 = time.perf_counter()
        code_, _ = post_json(
            f"{base}/api/reservations",
            {"seat_id": seat_id, "reserve_date": _today_bj().isoformat(),
             "slot_id": slot_id},
            token=token, headers={"X-Lock-Mode": mode},
        )
        dt = (time.perf_counter() - t0) * 1000
        with lock:
            latencies.append(dt)
            if code_ == 200:
                success += 1
            elif code_ == 409:
                conflict += 1
            else:
                error += 1

    print(f"[bench] 并发 {concurrency}，总请求 {users}，座位 {len(set(targets))} 个，"
          f"模式 {mode}（缓存 {health.get('cache', '?')}）")
    if len(tokens) < users:
        print(f"[bench] 警告：只登录成功 {len(tokens)} 个账号，实际请求数按账号数计算。"
              f"请执行 python -m scripts.init_db --reset 生成更多压测账号。")
    if mode == "redis" and health.get("cache") != "redis":
        print("[bench] 警告：当前后端未启用 Redis（cache=degraded），"
              "本次统计实际走的是数据库唯一索引路径，结果与 --mode db 相同。")
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(concurrency, 200)) as pool:
        list(pool.map(one, zip(tokens, targets)))
    elapsed = time.perf_counter() - start

    oversold = max(0, success - len(set(targets)))
    return {
        "mode": mode,
        "cache": health.get("cache"),
        "concurrency": concurrency,
        "seat_pool": len(set(targets)),
        "requests": users,
        "success": success,
        "conflict": conflict,
        "error": error,
        "oversold": oversold,
        "elapsed_sec": round(elapsed, 3),
        "tps": round(success / elapsed, 1) if elapsed > 0 else 0,
        "p50_ms": round(statistics.median(latencies), 1) if latencies else 0,
        "p95_ms": round(percentile(latencies, 95), 1),
        "max_ms": round(max(latencies), 1) if latencies else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="并发对照实验")
    parser.add_argument("--mode", choices=["nolock", "db", "redis"], required=True)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=200, help="总请求数")
    parser.add_argument("--seats", type=int, default=100, help="争抢的座位数")
    parser.add_argument("--concurrency", type=int, default=100, help="并发线程数")
    parser.add_argument("--room-id", type=int, default=1)
    parser.add_argument("--slot-id", type=int, default=1)
    parser.add_argument("--out", default="", help="结果写入的 json 文件")
    args = parser.parse_args()

    if args.mode == "nolock":
        result = run_nolock(args.concurrency, args.seats)
    else:
        result = run_http(args.url, args.mode, args.users, args.seats,
                          args.concurrency, args.room_id, args.slot_id)

    print("\n===== 实验结果 =====")
    for k, v in result.items():
        print(f"  {k:<15}: {v}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        print(f"\n结果已写入 {args.out}")


if __name__ == "__main__":
    main()
