from __future__ import annotations

from src.core.config import get_settings
from src.schemas.students import ImportResult, TranscriptResponse

from ..http_base import HttpAdapterClient
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
        return TranscriptResponse.model_validate(response.json())

    async def import_graduate_check(self, raw: bytes) -> ImportResult:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.STUDENT_DATA_URL, module="05", timeout_policy=settings.timeouts.write
        )
        try:
            response = await client.request(
                "POST",
                PATH_IMPORT_GRADUATE_CHECK,
                content=raw,
                headers={"Content-Type": "text/html"},
            )
        finally:
            await client.aclose()
        return ImportResult.model_validate(response.json())
