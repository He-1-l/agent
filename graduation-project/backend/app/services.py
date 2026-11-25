# -*- coding: utf-8 -*-
"""业务服务层：预约、取消、签到、签退、违约处理。

核心是 reserve() 中的三层防超卖：
  第一层  Redis Lua 原子扣减（缓存可用时）
  第二层  数据库联合唯一索引兜底（任何情况都生效）
  第三层  Redis 不可用时自动降级为"查询 + 唯一索引"的乐观锁路径
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .cache import cache
from .config import settings
from .models import (
    CheckinRecord, CreditLog, Reservation, Seat, Student, TimeSlot, Waitlist,
)


# ----------------------------------------------------------------------
# 小工具
# ----------------------------------------------------------------------
def _conflict(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)


def _bad(msg: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


def adjust_credit(db: Session, student: Student, delta: int, reason: str,
                  reservation_id: Optional[int] = None) -> None:
    """调整信用分并留流水。"""
    if delta == 0:
        return
    student.credit_score = max(0, min(100, student.credit_score + delta))
    db.add(CreditLog(
        student_id=student.id,
        change_value=delta,
        reason=reason,
        reservation_id=reservation_id,
    ))


def has_active(db: Session, seat_id: int, d: date, slot_id: int) -> bool:
    row = db.execute(
        select(Reservation.id).where(
            Reservation.seat_id == seat_id,
            Reservation.reserve_date == d,
            Reservation.slot_id == slot_id,
            Reservation.is_active == 1,
        ).limit(1)
    ).first()
    return row is not None


# ----------------------------------------------------------------------
# 预约
# ----------------------------------------------------------------------
def reserve(db: Session, student: Student, seat_id: int, d: date,
            slot_id: int, mode: str = "auto") -> Reservation:
    slot = db.get(TimeSlot, slot_id)
    if not slot or slot.status != 1:
        raise _bad("该时段不存在或已关闭")

    seat = db.get(Seat, seat_id)
    if not seat or seat.status != 1:
        raise _bad("该座位不存在或维修中")

    today = date.today()
    if d < today or d > today + timedelta(days=1):
        raise _bad("仅可预约今天与明天的座位")

    # ---- 时段可用性判断 ----
    # 设计要点：时段开始后仍然允许预约，因为「超时未签到」会释放座位，
    # 那个座位必须能被后来的人接走，否则释放就没有意义。
    # 但要满足两个条件：
    #   1) 时段还没结束，且距结束至少 MIN_REMAINING_MINUTES 分钟；
    #   2) 签到截止时间从「现在」重新计算，不能沿用时段开始时间，
    #      否则中途抢到的座位会立刻被判违约。
    now = datetime.now()
    slot_start = datetime.combine(d, slot.start_time)
    slot_end = datetime.combine(d, slot.end_time)

    if now >= slot_end:
        raise _bad("该时段已结束，请选择后面的时段")

    if now < slot_start:
        # 还没开始：签到截止 = 时段开始 + 宽限期（原有逻辑）
        deadline = slot_start + timedelta(minutes=settings.CHECKIN_GRACE_MINUTES)
    else:
        # 时段进行中：这是「捡漏」被释放的座位
        remaining = (slot_end - now).total_seconds() / 60
        if remaining < settings.MIN_REMAINING_MINUTES:
            raise _bad(
                f"该时段只剩 {int(remaining)} 分钟，"
                f"不足 {settings.MIN_REMAINING_MINUTES} 分钟，请选择后面的时段"
            )
        # 签到截止从当前时间算起，但不得超过时段结束
        deadline = min(
            now + timedelta(minutes=settings.CHECKIN_GRACE_MINUTES),
            slot_end,
        )

    if student.credit_score < settings.MIN_CREDIT_TO_RESERVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"信用分 {student.credit_score} 低于 {settings.MIN_CREDIT_TO_RESERVE}，暂不能预约",
        )

    daily = db.execute(
        select(func.count(Reservation.id)).where(
            Reservation.student_id == student.id,
            Reservation.reserve_date == d,
            Reservation.is_active == 1,
        )
    ).scalar_one()
    if daily >= settings.MAX_RESERVE_PER_DAY:
        raise _bad(f"每人每日最多预约 {settings.MAX_RESERVE_PER_DAY} 个时段")

    # 不能重复预约同一时段
    duplicated = db.execute(
        select(Reservation.id).where(
            Reservation.student_id == student.id,
            Reservation.reserve_date == d,
            Reservation.slot_id == slot_id,
            Reservation.is_active == 1,
        ).limit(1)
    ).first()
    if duplicated:
        raise _conflict("你在该时段已有预约")

    use_cache = False
    if mode == "auto":
        use_cache = cache.available
    elif mode == "redis":
        use_cache = cache.available

    if use_cache:
        got = cache.acquire(seat.room_id, d, slot_id, seat_id)
        if got is False:
            raise _conflict("该座位已被预约，请换一个")
        # got is None 表示缓存异常，已自动降级，继续走数据库兜底
        use_cache = got is True

    res = Reservation(
        student_id=student.id,
        room_id=seat.room_id,
        seat_id=seat_id,
        reserve_date=d,
        slot_id=slot_id,
        status=0,
        is_active=1,
        checkin_deadline=deadline,   # 上面按「是否已开始」分别算好了
    )
    db.add(res)
    try:
        db.commit()
    except IntegrityError:
        # 第二层兜底：唯一索引拦下了并发重复写入
        db.rollback()
        if use_cache:
            cache.release(seat.room_id, d, slot_id, seat_id)
        raise _conflict("该座位刚刚被他人抢走（唯一约束拦截）") from None
    except Exception:
        db.rollback()
        if use_cache:
            cache.release(seat.room_id, d, slot_id, seat_id)
        raise

    db.refresh(res)
    _notify_seat(seat.room_id, d, slot_id, seat_id, "reserved")
    return res


# ----------------------------------------------------------------------
# 取消 / 签到 / 签退
# ----------------------------------------------------------------------
def cancel(db: Session, student: Student, reservation_id: int) -> Reservation:
    res = db.get(Reservation, reservation_id)
    if not res or res.student_id != student.id:
        raise HTTPException(status_code=404, detail="预约不存在")
    if res.status not in (0, 1):
        raise _bad("当前状态不能取消")

    res.status = 3
    res.is_active = None  # 释放唯一索引位
    adjust_credit(db, student, -settings.CANCEL_PENALTY, "取消预约", res.id)
    db.commit()
    cache.release(res.room_id, res.reserve_date, res.slot_id, res.seat_id)
    _notify_seat(res.room_id, res.reserve_date, res.slot_id, res.seat_id, "released")
    _promote_waitlist(db, res.room_id, res.reserve_date, res.slot_id)
    return res


def checkin(db: Session, student: Student, reservation_id: int) -> Reservation:
    res = db.get(Reservation, reservation_id)
    if not res or res.student_id != student.id:
        raise HTTPException(status_code=404, detail="预约不存在")
    if res.status == 1:
        return res
    if res.status != 0:
        raise _bad("该预约不可签到")
    now = datetime.now()
    if res.checkin_deadline and now > res.checkin_deadline:
        raise _bad("已超过签到时限，座位已被释放")

    res.status = 1
    db.add(CheckinRecord(reservation_id=res.id, checkin_time=now))
    db.commit()
    _notify_seat(res.room_id, res.reserve_date, res.slot_id, res.seat_id, "checked_in")
    return res


def checkout(db: Session, student: Student, reservation_id: int) -> Reservation:
    res = db.get(Reservation, reservation_id)
    if not res or res.student_id != student.id:
        raise HTTPException(status_code=404, detail="预约不存在")
    if res.status != 1:
        raise _bad("尚未签到，无法签退")

    now = datetime.now()
    rec = db.execute(
        select(CheckinRecord).where(CheckinRecord.reservation_id == res.id)
    ).scalar_one_or_none()
    if rec:
        rec.checkout_time = now
        rec.duration_minutes = int((now - rec.checkin_time).total_seconds() // 60)

    res.status = 2
    res.is_active = None
    db.commit()
    cache.release(res.room_id, res.reserve_date, res.slot_id, res.seat_id)
    _notify_seat(res.room_id, res.reserve_date, res.slot_id, res.seat_id, "released")
    _promote_waitlist(db, res.room_id, res.reserve_date, res.slot_id)
    return res


# ----------------------------------------------------------------------
# 超时未签到：由后台任务定期调用
# ----------------------------------------------------------------------
def expire_no_show(db: Session) -> int:
    now = datetime.now()
    rows = db.execute(
        select(Reservation).where(
            Reservation.status == 0,
            Reservation.is_active == 1,
            Reservation.checkin_deadline < now,
        )
    ).scalars().all()

    for res in rows:
        res.status = 4
        res.is_active = None
        student = db.get(Student, res.student_id)
        if student:
            adjust_credit(db, student, -settings.NO_SHOW_PENALTY, "超时未签到", res.id)
        cache.release(res.room_id, res.reserve_date, res.slot_id, res.seat_id)
        _notify_seat(res.room_id, res.reserve_date, res.slot_id, res.seat_id, "released")
    if rows:
        db.commit()
    return len(rows)


# ----------------------------------------------------------------------
# 候补队列
# ----------------------------------------------------------------------
def join_waitlist(db: Session, student: Student, room_id: int, d: date, slot_id: int) -> Waitlist:
    last = db.execute(
        select(func.max(Waitlist.queue_no)).where(
            Waitlist.room_id == room_id,
            Waitlist.reserve_date == d,
            Waitlist.slot_id == slot_id,
            Waitlist.status == 0,
        )
    ).scalar_one_or_none() or 0
    item = Waitlist(
        student_id=student.id, room_id=room_id, reserve_date=d,
        slot_id=slot_id, queue_no=last + 1, status=0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _promote_waitlist(db: Session, room_id: int, d: date, slot_id: int) -> None:
    """有座位释放时，按排队序号补位（这里只做状态标记，实际通知可由站内信扩展）。"""
    item = db.execute(
        select(Waitlist).where(
            Waitlist.room_id == room_id,
            Waitlist.reserve_date == d,
            Waitlist.slot_id == slot_id,
            Waitlist.status == 0,
        ).order_by(Waitlist.queue_no).limit(1)
    ).scalar_one_or_none()
    if item:
        item.status = 1
        db.commit()


# ----------------------------------------------------------------------
# WebSocket 广播（延迟导入，避免循环依赖）
# ----------------------------------------------------------------------
def _notify_seat(room_id: int, d: date, slot_id: int, seat_id: int, event: str) -> None:
    try:
        from .routers.ws import manager

        manager.broadcast_threadsafe(room_id, {
            "event": event,
            "seat_id": seat_id,
            "date": d.isoformat(),
            "slot_id": slot_id,
        })
    except Exception:  # noqa: BLE001
        pass
