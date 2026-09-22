from __future__ import annotations

from src.core.config import get_settings

from .interfaces import (
    AnswerGenerator,
    ChatRouter,
    CourseCatalog,
    Explainer,
    LogSink,
    NotReadyAnswerGenerator,
    PlanEngine,
    StudentData,
)


def get_course_catalog() -> CourseCatalog:
    mode = get_settings().ADAPTER_04
    if mode == "mock":
        from .mock.course_catalog import MockCourseCatalog

        return MockCourseCatalog()
    if mode == "inprocess":
        from .inprocess.course_catalog import InprocessCourseCatalog

        return InprocessCourseCatalog()
    if mode == "http":
        from .http.course_catalog import HttpCourseCatalog

        return HttpCourseCatalog()
    raise ValueError(f"ADAPTER_04 ไม่รู้จัก: {mode!r}")


def get_student_data() -> StudentData:
    mode = get_settings().ADAPTER_05
    if mode == "mock":
        from .mock.student_data import MockStudentData

        return MockStudentData()
    if mode == "inprocess":
        from .inprocess.student_data import InprocessStudentData

        return InprocessStudentData()
    if mode == "http":
        from .http.student_data import HttpStudentData

        return HttpStudentData()
    raise ValueError(f"ADAPTER_05 ไม่รู้จัก: {mode!r}")


def get_plan_engine() -> PlanEngine:
    mode = get_settings().ADAPTER_06
    if mode == "mock":
        from .mock.plan_engine import MockPlanEngine

        return MockPlanEngine()
    if mode == "http":
        from .http.plan_engine import HttpPlanEngine

        return HttpPlanEngine()
    raise ValueError(f"ADAPTER_06 ไม่รองรับ inprocess (06 ไม่มี parser ในตัว) หรือค่าไม่รู้จัก: {mode!r}")


def get_explainer() -> Explainer:
    mode = get_settings().ADAPTER_07
    if mode == "mock":
        from .mock.explainer import MockExplainer

        return MockExplainer()
    if mode == "http":
        from .http.explainer import HttpExplainer

        return HttpExplainer()
    raise ValueError(f"ADAPTER_07 ไม่รองรับ inprocess หรือค่าไม่รู้จัก: {mode!r}")


def get_log_sink() -> LogSink:
    mode = get_settings().ADAPTER_08
    if mode == "mock":
        from .mock.log_sink import MockLogSink

        return MockLogSink()
    if mode == "http":
        from .http.log_sink import HttpLogSink

        return HttpLogSink()
    raise ValueError(f"ADAPTER_08 ไม่รองรับ inprocess หรือค่าไม่รู้จัก: {mode!r}")


def get_chat_router() -> ChatRouter:
    # 03 ใช้ http เสมอตาม CLAUDE.md ข้อ 7 (ไม่มี mock/inprocess ให้เลือกผ่าน ADAPTER)
    from .http.chat_router import HttpChatRouter

    return HttpChatRouter()


def get_answer_generator() -> AnswerGenerator:
    # ยังไม่มี contract จริงที่ยืนยันแล้วจากทีม 07 สำหรับการสร้างคำตอบแบบ stream (ต่างจาก Explainer ที่ใช้
    # อธิบายแผนที่บันทึกแล้ว) — production path จึงตอบ error เสมอ ทดสอบ flow จริงต้อง override ด้วย fake
    return NotReadyAnswerGenerator()
