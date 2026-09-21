from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (UniqueConstraint("student_id", "term", "name", name="uq_plans_student_term_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("students.student_id"), nullable=False, index=True
    )
    term: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # ผลตรวจล่าสุด: ตอนนี้ POST /plans ไม่เรียก 05/06 (ตาม PLAN.md 4.3 ที่ระบุ GET/POST /plans ว่าเรียกไปที่ DB
    # เฉยๆ) จึงเป็น null เสมอ — ถ้าทีมต้องการให้บันทึกผลตรวจตอน save ด้วย ต้องยืนยันเพิ่ม (ดู PROGRESS.md)
    last_validation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list[PlanItem]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanItem.position"
    )


class PlanItem(Base):
    __tablename__ = "plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # section_id ไม่มี FK เพราะตาราง sections เป็นของโมดูล 04/05 ไม่ใช่ของ 02 (PLAN.md 3.1)
    section_id: Mapped[str] = mapped_column(String(50), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plan: Mapped[Plan] = relationship(back_populates="items")
