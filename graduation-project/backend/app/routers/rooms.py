# -*- coding: utf-8 -*-
"""资源路由：场馆、自习室、时段、座位平面图。"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_student
from ..models import Building, Reservation, Room, Seat, Student, TimeSlot
from ..schemas import BuildingOut, RoomOut, RoomSeatMap, SeatState, SlotOut
from ..timeutil import today_bj

router = APIRouter(prefix="/api", tags=["资源"])


@router.get("/buildings", response_model=List[BuildingOut], summary="场馆列表")
def list_buildings(db: Session = Depends(get_db)):
    return db.execute(
        select(Building).where(Building.status == 1).order_by(Building.id)
    ).scalars().all()


@router.get("/rooms", response_model=List[RoomOut], summary="自习室列表")
def list_rooms(
    building_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Room).where(Room.status == 1)
    if building_id:
        stmt = stmt.where(Room.building_id == building_id)
    return db.execute(stmt.order_by(Room.id)).scalars().all()


@router.get("/slots", response_model=List[SlotOut], summary="时段列表")
def list_slots(db: Session = Depends(get_db)):
    return db.execute(
        select(TimeSlot).where(TimeSlot.status == 1).order_by(TimeSlot.seq)
    ).scalars().all()


@router.get("/rooms/{room_id}/seats", response_model=RoomSeatMap, summary="座位平面图")
def room_seat_map(
    room_id: int,
    reserve_date: date = Query(default_factory=today_bj),
    slot_id: int = Query(default=1),
    _: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="自习室不存在")

    seats = db.execute(
        select(Seat).where(Seat.room_id == room_id).order_by(Seat.row_idx, Seat.col_idx)
    ).scalars().all()

    taken = set(db.execute(
        select(Reservation.seat_id).where(
            Reservation.room_id == room_id,
            Reservation.reserve_date == reserve_date,
            Reservation.slot_id == slot_id,
            Reservation.is_active == 1,
        )
    ).scalars().all())

    states = []
    for s in seats:
        if s.status != 1:
            state = "maintenance"
        elif s.id in taken:
            state = "reserved"
        else:
            state = "free"
        states.append(SeatState(
            id=s.id, seat_no=s.seat_no, row_idx=s.row_idx,
            col_idx=s.col_idx, has_power=s.has_power, state=state,
        ))

    return RoomSeatMap(room=RoomOut.model_validate(room), date=reserve_date,
                       slot_id=slot_id, seats=states)
