# -*- coding: utf-8 -*-
"""ORM 模型：11 张业务表，与《02-数据库设计.sql》保持一致。"""
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


class Student(Base):
    __tablename__ = "student"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_no = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    college = Column(String(100))
    major = Column(String(100))
    class_name = Column(String(50))
    phone = Column(String(20))
    password_hash = Column(String(200), nullable=False)
    credit_score = Column(Integer, nullable=False, default=100)
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.now)


class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    real_name = Column(String(50))
    role = Column(String(20), default="ADMIN")
    status = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)


class Building(Base):
    __tablename__ = "building"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    location = Column(String(200))
    open_time = Column(Time, default=time(7, 0))
    close_time = Column(Time, default=time(22, 30))
    status = Column(Integer, default=1)

    rooms = relationship("Room", back_populates="building")


class Room(Base):
    __tablename__ = "room"

    id = Column(Integer, primary_key=True, autoincrement=True)
    building_id = Column(Integer, ForeignKey("building.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    floor = Column(Integer, default=1)
    row_count = Column(Integer, default=5)
    col_count = Column(Integer, default=8)
    seat_count = Column(Integer, default=40)
    has_ac = Column(Integer, default=1)
    has_power = Column(Integer, default=1)
    status = Column(Integer, default=1)

    building = relationship("Building", back_populates="rooms")
    seats = relationship("Seat", back_populates="room")


class Seat(Base):
    __tablename__ = "seat"
    __table_args__ = (UniqueConstraint("room_id", "seat_no", name="uk_room_seat"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False, index=True)
    seat_no = Column(String(10), nullable=False)
    row_idx = Column(Integer, nullable=False)
    col_idx = Column(Integer, nullable=False)
    has_power = Column(Integer, default=1)
    status = Column(Integer, default=1)  # 1 可用 / 0 维修

    room = relationship("Room", back_populates="seats")


class TimeSlot(Base):
    __tablename__ = "time_slot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    seq = Column(Integer, nullable=False, unique=True)
    status = Column(Integer, default=1)


class Reservation(Base):
    """预约记录表 —— 防超卖的关键在下面这个联合唯一索引。

    (seat_id, reserve_date, slot_id, is_active) 唯一。
    is_active 有效时为 1，取消/违约时置为 NULL，
    利用"唯一索引允许多个 NULL"的特性，既能阻止有效记录重复，
    又允许同一座位被取消后重新预约。
    """
    __tablename__ = "reservation"
    __table_args__ = (
        UniqueConstraint("seat_id", "reserve_date", "slot_id", "is_active",
                         name="uk_seat_date_slot_active"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False, index=True)
    seat_id = Column(Integer, ForeignKey("seat.id"), nullable=False, index=True)
    reserve_date = Column(Date, nullable=False, default=date.today)
    slot_id = Column(Integer, ForeignKey("time_slot.id"), nullable=False)
    status = Column(Integer, nullable=False, default=0)  # 0待签到 1已签到 2已完成 3已取消 4违约
    is_active = Column(Integer, nullable=True, default=1)
    checkin_deadline = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now, index=True)


class CheckinRecord(Base):
    __tablename__ = "checkin_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    reservation_id = Column(Integer, ForeignKey("reservation.id"), unique=True, nullable=False)
    checkin_time = Column(DateTime, nullable=False)
    checkout_time = Column(DateTime)
    duration_minutes = Column(Integer)


class CreditLog(Base):
    __tablename__ = "credit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student.id"), nullable=False, index=True)
    change_value = Column(Integer, nullable=False)
    reason = Column(String(200), nullable=False)
    reservation_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)


class Waitlist(Base):
    __tablename__ = "waitlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student.id"), nullable=False)
    room_id = Column(Integer, nullable=False)
    reserve_date = Column(Date, nullable=False)
    slot_id = Column(Integer, nullable=False)
    queue_no = Column(Integer, nullable=False)
    status = Column(Integer, default=0)  # 0排队 1已补位 2放弃 3过期
    created_at = Column(DateTime, default=datetime.now)


class Announcement(Base):
    __tablename__ = "announcement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    publisher_id = Column(Integer)
    status = Column(Integer, default=1)
    publish_time = Column(DateTime, default=datetime.now)
