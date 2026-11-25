# -*- coding: utf-8 -*-
"""认证路由：注册、登录、当前用户。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_student
from ..models import Admin, Student
from ..schemas import LoginIn, RegisterIn, StudentOut, TokenOut
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=TokenOut, summary="学号注册")
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    exists = db.execute(
        select(Student).where(Student.student_no == payload.student_no)
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="该学号已注册")

    student = Student(
        student_no=payload.student_no,
        name=payload.name,
        college=payload.college,
        major=payload.major,
        class_name=payload.class_name,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        credit_score=100,
        status=1,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    token = create_token(str(student.id), role="student")
    return TokenOut(access_token=token, role="student", name=student.name)


@router.post("/login", response_model=TokenOut, summary="学生登录")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    student = db.execute(
        select(Student).where(Student.student_no == payload.student_no)
    ).scalar_one_or_none()
    if not student or not verify_password(payload.password, student.password_hash):
        raise HTTPException(status_code=401, detail="学号或密码错误")
    if student.status != 1:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_token(str(student.id), role="student")
    return TokenOut(access_token=token, role="student", name=student.name)


@router.post("/admin/login", response_model=TokenOut, summary="管理员登录")
def admin_login(payload: LoginIn, db: Session = Depends(get_db)):
    admin = db.execute(
        select(Admin).where(Admin.username == payload.student_no)
    ).scalar_one_or_none()
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    token = create_token(str(admin.id), role="admin")
    return TokenOut(access_token=token, role="admin", name=admin.real_name or "管理员")


@router.get("/me", response_model=StudentOut, summary="当前学生信息")
def me(student: Student = Depends(get_current_student)):
    return student
