# -*- coding: utf-8 -*-
"""管理端路由：占用统计、预约查询、学生管理、处罚与信用分管理。"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..cache import cache
from ..config import settings
from ..db import get_db
from ..deps import get_current_admin
from ..models import Admin, CreditLog, Reservation, Room, Seat, Student, TimeSlot
from ..schemas import (
    AdminRoomSeatMap, AdminSeatState,
    CreditAdjustIn, CreditLogOut, OverviewOut, PunishRecordOut, RoomOut,
    StudentOut, UsageRow,
)

router = APIRouter(prefix="/api/admin", tags=["管理端"])


def _slot_name(slot: TimeSlot) -> str:
    return f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"


@router.get("/overview", response_model=OverviewOut, summary="监控大屏概览")
def overview(
    stat_date: date = Query(default_factory=date.today),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rooms = db.execute(select(Room).where(Room.status == 1).order_by(Room.id)).scalars().all()
    slots = db.execute(select(TimeSlot).order_by(TimeSlot.seq)).scalars().all()
    seat_total = sum(r.seat_count for r in rooms) or 1

    counts = dict(db.execute(
        select(Reservation.room_id, func.count(Reservation.id))
        .where(Reservation.reserve_date == stat_date, Reservation.is_active == 1)
        .group_by(Reservation.room_id)
    ).all())

    rows: List[UsageRow] = []
    for room in rooms:
        for slot in slots:
            reserved = db.execute(
                select(func.count(Reservation.id)).where(
                    Reservation.room_id == room.id,
                    Reservation.reserve_date == stat_date,
                    Reservation.slot_id == slot.id,
                    Reservation.is_active == 1,
                )
            ).scalar_one()
            rows.append(UsageRow(
                room_id=room.id, room_name=room.name,
                slot_id=slot.id, slot_name=_slot_name(slot),
                reserved=reserved, total=room.seat_count,
                usage_rate=round(reserved / (room.seat_count or 1) * 100, 2),
            ))

    total = db.execute(
        select(func.count(Reservation.id)).where(Reservation.reserve_date == stat_date)
    ).scalar_one()
    no_show = db.execute(
        select(func.count(Reservation.id)).where(
            Reservation.reserve_date == stat_date, Reservation.status == 4)
    ).scalar_one()

    return OverviewOut(
        date=stat_date,
        total_reservations=total,
        active_reservations=sum(counts.values()),
        no_show=no_show,
        seat_count=seat_total,
        usage_rate=round(sum(counts.values()) / seat_total * 100, 2),
        cache_enabled=cache.available,
        rows=rows,
    )


@router.get("/reservations", summary="预约记录查询")
def list_reservations(
    stat_date: date = Query(default_factory=date.today),
    limit: int = Query(default=200, le=1000),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Reservation, Student.name, Seat.seat_no, Room.name, TimeSlot)
        .join(Student, Student.id == Reservation.student_id)
        .join(Seat, Seat.id == Reservation.seat_id)
        .join(Room, Room.id == Reservation.room_id)
        .join(TimeSlot, TimeSlot.id == Reservation.slot_id)
        .where(Reservation.reserve_date == stat_date)
        .order_by(Reservation.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "student_name": name,
            "seat_no": seat_no,
            "room_name": room_name,
            "slot_id": r.slot_id,
            "slot_name": _slot_name(slot),
            "reserve_date": str(r.reserve_date),
            "created_at": r.created_at.strftime("%H:%M:%S") if r.created_at else "",
            "status": r.status,
        }
        for r, name, seat_no, room_name, slot in rows
    ]


@router.get("/students", response_model=List[StudentOut], summary="学生列表")
def list_students(
    keyword: Optional[str] = Query(default=None, description="按学号或姓名模糊搜索"),
    limit: int = Query(default=1000, le=5000),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """学生列表。

    默认按 id 倒序（最新注册的排在最前），避免新注册的学生因为分页被截断看不到。
    压测账号 bench* 默认不返回，需要时用 keyword 搜索。
    """
    stmt = select(Student)
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(Student.student_no.like(like), Student.name.like(like)))
    else:
        # 默认隐藏压测账号，让列表聚焦在真实用户上
        stmt = stmt.where(~Student.student_no.like("bench%"))

    return db.execute(
        stmt.order_by(Student.id.desc()).limit(limit)
    ).scalars().all()


@router.post("/students/{student_id}/status", summary="启用/禁用学生")
def toggle_student(
    student_id: int,
    status: int = Query(ge=0, le=1),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    student = db.get(Student, student_id)
    if student:
        student.status = status
        db.commit()
    return {"ok": True, "student_id": student_id, "status": status}


@router.get("/config", summary="当前运行配置（用于演示缓存降级）")
def current_config(_: Admin = Depends(get_current_admin)):
    return {
        "cache_enabled": cache.available,
        "redis_url": settings.REDIS_URL or "(未配置，已降级)",
        "database": settings.DATABASE_URL.split("://")[0],
        "checkin_grace_minutes": settings.CHECKIN_GRACE_MINUTES,
        "max_reserve_per_day": settings.MAX_RESERVE_PER_DAY,
        "min_credit_to_reserve": settings.MIN_CREDIT_TO_RESERVE,
        "no_show_penalty": settings.NO_SHOW_PENALTY,
    }


# ======================================================================
# 处罚与信用分管理
# ======================================================================
@router.get("/punishments", response_model=List[PunishRecordOut],
            summary="处罚记录列表（违约的预约）")
def list_punishments(
    student_id: Optional[int] = Query(default=None, description="只看某个学生"),
    limit: int = Query(default=100, le=500),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """列出所有被判为违约的预约，供管理员核对与撤销。"""
    stmt = (
        select(Reservation, Student, Seat, Room, TimeSlot)
        .join(Student, Student.id == Reservation.student_id)
        .join(Seat, Seat.id == Reservation.seat_id)
        .join(Room, Room.id == Reservation.room_id)
        .join(TimeSlot, TimeSlot.id == Reservation.slot_id)
        .where(Reservation.status == 4)          # 4 = 违约
        .order_by(Reservation.created_at.desc())
        .limit(limit)
    )
    if student_id:
        stmt = stmt.where(Reservation.student_id == student_id)

    return [
        PunishRecordOut(
            reservation_id=res.id,
            student_id=stu.id,
            student_name=stu.name,
            seat_no=seat.seat_no,
            room_name=room.name,
            reserve_date=res.reserve_date,
            slot_name=_slot_name(slot),
            status=res.status,
            checkin_deadline=res.checkin_deadline,
        )
        for res, stu, seat, room, slot in db.execute(stmt).all()
    ]


@router.post("/punishments/{reservation_id}/revoke",
             response_model=PunishRecordOut, summary="撤销一次违约处罚")
def revoke_punishment(
    reservation_id: int,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """撤销违约：把预约状态从「违约」改回「已取消」，并把扣掉的信用分加回来。

    注意两点：
      1. 只补回当时扣掉的分数，不是无脑恢复满 100 分；
      2. 会写一条信用分流水，说明「由哪位管理员撤销」，可追溯。
    """
    res = db.get(Reservation, reservation_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if res.status != 4:
        raise HTTPException(status_code=400, detail="该记录不是违约状态，无需撤销")

    student = db.get(Student, res.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 找出这条预约对应的扣分流水，原样补回
    log = db.execute(
        select(CreditLog).where(
            CreditLog.reservation_id == res.id,
            CreditLog.change_value < 0,
        ).order_by(CreditLog.id.desc()).limit(1)
    ).scalar_one_or_none()

    refund = abs(log.change_value) if log else settings.NO_SHOW_PENALTY
    student.credit_score = min(100, student.credit_score + refund)
    db.add(CreditLog(
        student_id=student.id,
        change_value=refund,
        reason=f"管理员 {admin.username} 撤销违约（预约 #{res.id}）",
        reservation_id=res.id,
    ))

    # 状态改为「已取消」，is_active 置 NULL，不再占用唯一索引位
    res.status = 3
    res.is_active = None
    db.commit()

    seat = db.get(Seat, res.seat_id)
    room = db.get(Room, res.room_id)
    slot = db.get(TimeSlot, res.slot_id)

    return PunishRecordOut(
        reservation_id=res.id,
        student_id=student.id,
        student_name=student.name,
        seat_no=seat.seat_no if seat else "",
        room_name=room.name if room else "",
        reserve_date=res.reserve_date,
        slot_name=_slot_name(slot) if slot else "",
        status=res.status,
        checkin_deadline=res.checkin_deadline,
    )


@router.post("/students/{student_id}/credit", response_model=StudentOut,
             summary="手动调整学生信用分")
def adjust_student_credit(
    student_id: int,
    payload: CreditAdjustIn,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员手动加分或扣分，用于处理申诉、奖励等场景。"""
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if payload.amount == 0:
        raise HTTPException(status_code=400, detail="变动值不能为 0")

    student.credit_score = max(0, min(100, student.credit_score + payload.amount))
    db.add(CreditLog(
        student_id=student.id,
        change_value=payload.amount,
        reason=f"{payload.reason}（操作人：{admin.username}）",
    ))
    db.commit()
    db.refresh(student)
    return student


@router.get("/students/{student_id}/credit-logs", response_model=List[CreditLogOut],
            summary="查看某学生的信用分流水")
def student_credit_logs(
    student_id: int,
    limit: int = Query(default=50, le=200),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return db.execute(
        select(CreditLog)
        .where(CreditLog.student_id == student_id)
        .order_by(CreditLog.created_at.desc())
        .limit(limit)
    ).scalars().all()


# ======================================================================
# 座位占用详情：管理员能看到「哪个座位被谁占了」
# ======================================================================
@router.get("/rooms/{room_id}/seats", response_model=AdminRoomSeatMap,
            summary="管理端座位占用详情（含占用者信息）")
def admin_room_seat_map(
    room_id: int,
    reserve_date: date = Query(default_factory=date.today),
    slot_id: int = Query(default=1),
    _: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """与学生端座位图的区别：每个被占座位都会带上占用者姓名、学号与预约状态。

    数据来源是一次 left join：座位左连接「该日期该时段的有效预约」，
    再连接学生表取姓名。没有匹配到预约的座位就是空闲。
    """
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="自习室不存在")

    slot = db.get(TimeSlot, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="时段不存在")

    rows = db.execute(
        select(Seat, Reservation, Student)
        .outerjoin(
            Reservation,
            (Reservation.seat_id == Seat.id)
            & (Reservation.reserve_date == reserve_date)
            & (Reservation.slot_id == slot_id)
            & (Reservation.is_active == 1),
        )
        .outerjoin(Student, Student.id == Reservation.student_id)
        .where(Seat.room_id == room_id)
        .order_by(Seat.row_idx, Seat.col_idx)
    ).all()

    seats = []
    for seat, res, stu in rows:
        if seat.status != 1:
            state = "maintenance"
        elif res is not None:
            state = "reserved"
        else:
            state = "free"

        seats.append(AdminSeatState(
            id=seat.id,
            seat_no=seat.seat_no,
            row_idx=seat.row_idx,
            col_idx=seat.col_idx,
            has_power=seat.has_power,
            state=state,
            student_name=stu.name if stu else None,
            student_no=stu.student_no if stu else None,
            reservation_id=res.id if res else None,
            checkin_deadline=res.checkin_deadline if res else None,
            res_status=res.status if res else None,
        ))

    return AdminRoomSeatMap(
        room=RoomOut.model_validate(room),
        date=reserve_date,
        slot_id=slot_id,
        slot_name=_slot_name(slot),
        seats=seats,
    )
