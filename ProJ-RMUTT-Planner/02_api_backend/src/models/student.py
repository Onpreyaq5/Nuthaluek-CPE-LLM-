from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Student(Base):
    """ตาราง students — โครง field เดาไว้เท่าที่ Prompt 4 ต้องใช้ (login/JWT) เพราะไม่มีไฟล์
    00_docs/05_data_model.md ในสภาพแวดล้อมนี้ — ต้องให้ทีมยืนยัน field เพิ่มเติมก่อนใช้งานจริง (ดู PROGRESS.md)
    """

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentPreference(Base):
    __tablename__ = "student_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("students.student_id"), unique=True, nullable=False, index=True
    )
    free_days: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    no_early_class: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
