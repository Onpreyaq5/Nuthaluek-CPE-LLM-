from __future__ import annotations

from src.core.config import get_settings
from src.schemas.students import ImportResult, TranscriptResponse

from ..inprocess_loader import load_module_package
from ..interfaces import StudentContext

_MOD05_ALIAS = "mod05"


class InprocessStudentData:
    """เรียก 05_data_integration ตรงในโปรเซสเดียวกัน — อ่านโค้ดของ 05 อย่างเดียว ห้ามแก้

    ทิ้ง student_id ที่ parse ได้จากไฟล์ ใช้ของ session แทนเสมอ (ตาม Prompt 3 ข้อ 5)
    """

    def __init__(self) -> None:
        self._mod = load_module_package(get_settings().MODULE_05_DIR, _MOD05_ALIAS)

    async def get_context(self, student_id: str) -> StudentContext:
        raise NotImplementedError(
            "05_data_integration ยังไม่มีฟังก์ชันสำหรับ get_context ใน inprocess mode "
            "(Prompt 3 ทำให้เฉพาะ import_graduate_check) — ใช้ ADAPTER_05=mock หรือ http แทน"
        )

    async def get_transcript(self, student_id: str) -> TranscriptResponse:
        raise NotImplementedError(
            "05_data_integration ยังไม่มีฟังก์ชันสำหรับ get_transcript ใน inprocess mode — "
            "ใช้ ADAPTER_05=mock หรือ http แทน"
        )

    async def import_graduate_check(self, raw: bytes) -> ImportResult:
        import importlib

        # load_module_package() โหลดแค่แพ็กเกจ mod05 เฉยๆ ไม่ทำให้ mod05.graduate_check/degree_plan
        # เป็น attribute อัตโนมัติ (Python ไม่ import submodule ให้เองถ้ายังไม่มีใคร import) —
        # ต้อง import_module() ตรงๆ ก่อนถึงจะเข้าถึงผ่าน attribute ได้ (mod05/src/__init__.py ของ 05 เองก็
        # ไม่ได้ import submodule ให้ในนี้เหมือนกัน จึงต้องทำฝั่งเราเอง)
        graduate_check = importlib.import_module(f"{_MOD05_ALIAS}.graduate_check")
        degree_plan = importlib.import_module(f"{_MOD05_ALIAS}.degree_plan")

        audit = graduate_check.parse_graduate_check(raw)
        plan_input = degree_plan.build_plan_input(audit)

        # field ของ DegreeAudit/DegreePlanInput ยืนยันจากโค้ดจริงของ 05 แล้ว (ไม่ใช่เดาชื่อ field แบบเดิม)
        # แต่ "ความหมาย" ที่ควร map เข้า ImportResult (schema ของ 02) ยังไม่เคยคุยกับทีม 05 ตรงๆ —
        # ตีความที่สมเหตุสมผลที่สุดเท่าที่ทำได้ตอนนี้:
        #   imported_courses  = จำนวนวิชาทั้งหมดที่เจอในทรานสคริปต์ (audit.all_courses())
        #   retake_required   = รหัสวิชาที่เคยลงแล้วแต่ยังไม่ผ่าน (audit.failed_courses())
        #   credits_remaining = plan_input.remaining_total (หน่วยกิตที่ยังขาดตามเกณฑ์จบทั้งหมด)
        #   warnings          = ไม่มีแนวคิด "warning" ใน DegreeAudit/DegreePlanInput ของ 05 ตรงๆ —
        #                       ปล่อยว่างไว้แทนการเดาเนื้อหาเอง ต้องคุยกับทีม 05 ว่าควรมาจากไหน
        return ImportResult(
            imported_courses=len(audit.all_courses()),
            retake_required=[course.code for _, course in audit.failed_courses()],
            credits_remaining=plan_input.remaining_total or 0,
            warnings=[],
        )
