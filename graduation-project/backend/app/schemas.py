# -*- coding: utf-8 -*-
"""Pydantic 数据模型（请求/响应结构）。"""
from datetime import date, datetime, time
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------- 认证 ----------------------------
class RegisterIn(BaseModel):
    student_no: str = Field(..., min_length=4, max_length=20, description="学号")
    name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=64)
    college: Optional[str] = None
    major: Optional[str] = None
    class_name: Optional[str] = None
    phone: Optional[str] = None


class LoginIn(BaseModel):
    student_no: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "student"
    name: str = ""


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    name: str
    college: Optional[str] = None
    major: Optional[str] = None
    class_name: Optional[str] = None
    credit_score: int
    status: int


# ---------------------------- 资源 ----------------------------
class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: Optional[str] = None
    open_time: Optional[time] = None
    close_time: Optional[time] = None


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    name: str
    floor: int
    row_count: int
    col_count: int
    seat_count: int
    has_ac: int
    has_power: int


class SlotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: time
    end_time: time
    seq: int


class SeatState(BaseModel):
    id: int
    seat_no: str
    row_idx: int
    col_idx: int
    has_power: int
    state: str  # free / reserved / maintenance


class RoomSeatMap(BaseModel):
    room: RoomOut
    date: date
    slot_id: int
    seats: List[SeatState]


# ---------------------------- 预约 ----------------------------
class ReserveIn(BaseModel):
    seat_id: int
    reserve_date: date
    slot_id: int


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    room_id: int
    seat_id: int
    reserve_date: date
    slot_id: int
    status: int
    checkin_deadline: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ReservationDetail(ReservationOut):
    seat_no: str = ""
    room_name: str = ""
    slot_name: str = ""


class WaitlistIn(BaseModel):
    room_id: int
    reserve_date: date
    slot_id: int


class WaitlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    room_id: int
    reserve_date: date
    slot_id: int
    queue_no: int
    status: int


# ---------------------------- 统计 ----------------------------
class UsageRow(BaseModel):
    room_id: int
    room_name: str
    slot_id: int
    slot_name: str
    reserved: int
    total: int
    usage_rate: float


class OverviewOut(BaseModel):
    date: date
    total_reservations: int
    active_reservations: int
    no_show: int
    seat_count: int
    usage_rate: float
    cache_enabled: bool
    rows: List[UsageRow]


# ---------------------------- 管理端：处罚与信用分 ----------------------------
class CreditAdjustIn(BaseModel):
    amount: int = Field(..., ge=-100, le=100, description="变动值：恢复为正，扣减为负")
    reason: str = Field(default="管理员手动调整", max_length=200)


class CreditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    change_value: int
    reason: str
    reservation_id: Optional[int] = None
    created_at: Optional[datetime] = None


class PunishRecordOut(BaseModel):
    """一条可撤销的处罚记录，本质是一条被标记为违约的预约。"""

    reservation_id: int
    student_id: int
    student_name: str
    seat_no: str
    room_name: str
    reserve_date: date
    slot_name: str
    status: int
    checkin_deadline: Optional[datetime] = None


# ---------------------------- 管理端：座位占用详情 ----------------------------
class AdminSeatState(BaseModel):
    """管理端看到的座位状态：比学生端多一个「谁占的」。"""

    id: int
    seat_no: str
    row_idx: int
    col_idx: int
    has_power: int
    state: str                                  # free / reserved / maintenance
    student_name: Optional[str] = None          # 占用者姓名
    student_no: Optional[str] = None            # 占用者学号
    reservation_id: Optional[int] = None        # 对应的预约号
    checkin_deadline: Optional[datetime] = None
    res_status: Optional[int] = None            # 预约状态：0待签到 1已签到 2已完成


class AdminRoomSeatMap(BaseModel):
    room: RoomOut
    date: date
    slot_id: int
    slot_name: str
    seats: List[AdminSeatState]
