from __future__ import annotations

from src.core.config import get_settings
from src.schemas.students import ImportResult, TranscriptResponse

from ..http_base import HttpAdapterClient, raise_for_upstream
from ..interfaces import StudentContext

# ปลายทางของ 05 ยังไม่มีสัญญาจริง — PLACEHOLDER
PATH_GET_CONTEXT = "/students/{student_id}/context"
PATH_GET_TRANSCRIPT = "/students/{student_id}/transcript"
PATH_IMPORT_GRADUATE_CHECK = "/import/graduate-check"


class HttpStudentData:
    async def get_context(self, student_id: str) -> StudentContext:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.STUDENT_DATA_URL, module="05", timeout_policy=settings.timeouts.read
        )
        try:
            response = await client.request("GET", PATH_GET_CONTEXT.format(student_id=student_id))
        finally:
            await client.aclose()
        raise_for_upstream(response, "05")
        return StudentContext.model_validate(response.json())

    async def get_transcript(self, student_id: str) -> TranscriptResponse:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.STUDENT_DATA_URL, module="05", timeout_policy=settings.timeouts.read
        )
        try:
            response = await client.request("GET", PATH_GET_TRANSCRIPT.format(student_id=student_id))
        finally:
            await client.aclose()
        if response.status_code == 404:
            # 05 มี transcript เฉพาะคนที่นำเข้าไฟล์ตรวจสอบจบแล้ว ยังไม่นำเข้า = ยังไม่มีวิชา ไม่ใช่ error
            return TranscriptResponse(courses=[], credits_by_category={})
        raise_for_upstream(response, "05")
        return TranscriptResponse.model_validate(response.json())

    async def import_graduate_check(self, raw: bytes, student_id: str | None = None) -> ImportResult:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.STUDENT_DATA_URL, module="05", timeout_policy=settings.timeouts.write
        )
        try:
            response = await client.request(
                "POST",
                PATH_IMPORT_GRADUATE_CHECK,
                # ผูกผลนำเข้ากับคนที่ login ไม่ใช่รหัสในไฟล์ (ไฟล์บางแบบไม่มีรหัส ผลจะหายไปเฉย ๆ)
                params={"student_id": student_id} if student_id else None,
                content=raw,
                headers={"Content-Type": "text/html"},
            )
        finally:
            await client.aclose()
        raise_for_upstream(response, "05")
        return ImportResult.model_validate(response.json())
