# -*- coding: utf-8 -*-
"""预约路由：预约、取消、签到、签退、候补。"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..db import get_db
from ..deps import get_current_student, lock_mode
from ..models import Reservation, Room, Seat, Student, TimeSlot
from ..schemas import (
    ReservationDetail, ReservationOut, ReserveIn, WaitlistIn, WaitlistOut,
)

router = APIRouter(prefix="/api/reservations", tags=["预约"])


@router.post("", response_model=ReservationOut, summary="创建预约")
def create_reservation(
    payload: ReserveIn,
    mode: str = Depends(lock_mode),
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return services.reserve(
        db, student, payload.seat_id, payload.reserve_date, payload.slot_id, mode=mode
    )


@router.get("/mine", response_model=List[ReservationDetail], summary="我的预约")
def my_reservations(
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Reservation).where(Reservation.student_id == student.id)
        .order_by(Reservation.created_at.desc()).limit(100)
    ).scalars().all()

    seat_ids = {r.seat_id for r in rows}
    room_ids = {r.room_id for r in rows}
    slot_ids = {r.slot_id for r in rows}

    seats = {s.id: s for s in db.execute(
        select(Seat).where(Seat.id.in_(seat_ids))).scalars().all()} if seat_ids else {}
    rooms = {r.id: r for r in db.execute(
        select(Room).where(Room.id.in_(room_ids))).scalars().all()} if room_ids else {}
    slots = {s.id: s for s in db.execute(
        select(TimeSlot).where(TimeSlot.id.in_(slot_ids))).scalars().all()} if slot_ids else {}

    result = []
    for r in rows:
        seat = seats.get(r.seat_id)
        room = rooms.get(r.room_id)
        slot = slots.get(r.slot_id)
        item = ReservationDetail.model_validate(r)
        item.seat_no = seat.seat_no if seat else ""
        item.room_name = room.name if room else ""
        item.slot_name = (
            f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}"
            if slot else ""
        )
        result.append(item)
    return result


@router.post("/{reservation_id}/cancel", response_model=ReservationOut, summary="取消预约")
def cancel(
    reservation_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return services.cancel(db, student, reservation_id)


@router.post("/{reservation_id}/checkin", response_model=ReservationOut, summary="签到")
def checkin(
    reservation_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return services.checkin(db, student, reservation_id)


@router.post("/{reservation_id}/checkout", response_model=ReservationOut, summary="签退")
def checkout(
    reservation_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return services.checkout(db, student, reservation_id)


@router.post("/waitlist", response_model=WaitlistOut, summary="加入候补队列")
def join_waitlist(
    payload: WaitlistIn,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    return services.join_waitlist(
        db, student, payload.room_id, payload.reserve_date, payload.slot_id
    )
