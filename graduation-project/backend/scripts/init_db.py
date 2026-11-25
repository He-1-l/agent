# -*- coding: utf-8 -*-
"""初始化数据库并写入演示数据。

用法：
    python -m scripts.init_db          # 建表 + 种子数据
    python -m scripts.init_db --reset  # 删库重建（慎用）
"""
import argparse
import os
import sys
from datetime import time

from sqlalchemy import select

# 允许从 backend 目录直接运行
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402
from app.models import (  # noqa: E402
    Admin, Announcement, Building, Room, Seat, Student, TimeSlot,
)
from app.security import hash_password  # noqa: E402

DEFAULT_PASSWORD = "123456"


def reset_database() -> None:
    print("[init] 删除全部表 ...")
    Base.metadata.drop_all(bind=engine)


def seed() -> None:
    db = SessionLocal()
    try:
        if db.execute(select(Building).limit(1)).first():
            print("[init] 检测到已有数据，跳过种子写入（如需重建请加 --reset）")
            return

        # 场馆
        lib = Building(name="图书馆", location="校园中心区 图书馆大楼",
                       open_time=time(7, 0), close_time=time(22, 30), status=1)
        teach = Building(name="第一教学楼", location="校园东区",
                         open_time=time(8, 0), close_time=time(22, 0), status=1)
        db.add_all([lib, teach])
        db.flush()

        # 自习室
        r1 = Room(building_id=lib.id, name="图书馆二层自习室", floor=2,
                  row_count=5, col_count=8, seat_count=40, has_ac=1, has_power=1)
        r2 = Room(building_id=lib.id, name="图书馆三层自习室", floor=3,
                  row_count=5, col_count=8, seat_count=40, has_ac=1, has_power=1)
        r3 = Room(building_id=teach.id, name="一教201自习室", floor=2,
                  row_count=4, col_count=6, seat_count=24, has_ac=0, has_power=1)
        db.add_all([r1, r2, r3])
        db.flush()

        # 座位：按 行×列 生成，编号 A-01 形式
        total = 0
        for room in (r1, r2, r3):
            for row in range(1, room.row_count + 1):
                for col in range(1, room.col_count + 1):
                    db.add(Seat(
                        room_id=room.id,
                        seat_no=f"{chr(64 + row)}-{col:02d}",
                        row_idx=row, col_idx=col,
                        has_power=1 if col <= 2 else 0,
                        status=1,
                    ))
                    total += 1
        print(f"[init] 生成座位 {total} 个")

        # 时段
        slots = [
            (time(8, 0), time(10, 0), 1), (time(10, 0), time(12, 0), 2),
            (time(13, 0), time(15, 0), 3), (time(15, 0), time(17, 0), 4),
            (time(18, 0), time(20, 0), 5), (time(20, 0), time(22, 0), 6),
        ]
        for st, et, seq in slots:
            db.add(TimeSlot(start_time=st, end_time=et, seq=seq, status=1))

        # 管理员
        db.add(Admin(username="admin", password_hash=hash_password(DEFAULT_PASSWORD),
                     real_name="系统管理员", role="SUPER", status=1))

        # 演示学生
        db.add(Student(student_no="2022010101", name="张三",
                       college="计算机学院", major="计算机科学与技术",
                       class_name="计科2201", phone="13800000001",
                       password_hash=hash_password(DEFAULT_PASSWORD),
                       credit_score=100, status=1))

        # 压测账号：bench0001 ~ bench0500（密码同 123456）
        for i in range(1, 501):
            db.add(Student(
                student_no=f"bench{i:04d}", name=f"压测用户{i}",
                college="计算机学院", major="计算机科学与技术",
                password_hash=hash_password(DEFAULT_PASSWORD),
                credit_score=100, status=1,
            ))

        db.add(Announcement(
            title="自习室预约规则说明",
            content="每日 06:00 开放次日预约；预约后需在时段开始后 15 分钟内完成签到，"
                    "超时系统自动释放座位并扣 5 分信用分。",
            publisher_id=1, status=1,
        ))
        db.commit()
        print(f"[init] 种子数据写入完成，管理员 admin/{DEFAULT_PASSWORD}，"
              f"演示学生 2022010101/{DEFAULT_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="先删表再重建")
    args = parser.parse_args()

    if args.reset:
        reset_database()
    init_db()
    seed()
    print("[init] 完成")
