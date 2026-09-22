"""06_schedule_conflict_engine - Student Data Adapter (Context Provider)
Resolves student academic history from 05 or memory fixtures
"""
from __future__ import annotations

import httpx
from ..config import get_settings
from ..models.schemas import StudentContextInput
from .providers import StudentContextNotFoundError, StudentContextProvider, UpstreamServiceError


class MemoryStudentContextProvider:
    """In-memory Student Context Provider สำหรับ Unit & Integration Tests"""
    def __init__(self, contexts: dict[str, StudentContextInput] | None = None):
        self._contexts: dict[str, StudentContextInput] = contexts or {}

    def set_context(self, student_ref: str, context: StudentContextInput) -> None:
        self._contexts[student_ref] = context

    async def get_context(self, student_ref: str) -> StudentContextInput:
        clean_ref = student_ref.strip()
        if clean_ref not in self._contexts:
            raise StudentContextNotFoundError(clean_ref)
        return self._contexts[clean_ref]


class HttpStudentContextProvider:
    """HTTP Client เรียกข้อมูล Student Context จากโมดูล 05 (05_data_integration)"""
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.data_integration_url).rstrip("/")
        self.timeout = timeout or settings.http_timeout_seconds

    async def get_context(self, student_ref: str) -> StudentContextInput:
        clean_ref = student_ref.strip()
        url = f"{self.base_url}/context/{clean_ref}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.get(url)
                if res.status_code == 404:
                    raise StudentContextNotFoundError(clean_ref)
                if res.status_code != 200:
                    raise UpstreamServiceError("05_data_integration", res.status_code, res.text)
                data = res.json()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise UpstreamServiceError("05_data_integration", 503, f"Cannot connect to 05: {exc}")

        passed = data.get("passed_courses") or data.get("completed_course_codes") or []
        failed = data.get("failed_courses") or []

        return StudentContextInput(
            student_id=clean_ref,
            passed_courses=[str(c) for c in passed],
            failed_courses=[str(c) for c in failed],
            gpax=data.get("gpax"),
        )
