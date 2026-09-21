from __future__ import annotations

from typing import Any

import httpx

from src.core.config import TimeoutPolicy
from src.core.errors import Upstream502Error
from src.core.middleware import get_request_id


class HttpAdapterClient:
    """httpx wrapper กลางสำหรับเรียกโมดูล 03-08: ผูก timeout/retry ตามนโยบายของแต่ละ
    ประเภทคำขอ (PLAN.md ตาราง 3.3) · retry เฉพาะ timeout/5xx · error ทุกแบบ -> UPSTREAM_502
    """

    def __init__(
        self,
        *,
        base_url: str,
        module: str,
        timeout_policy: TimeoutPolicy,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._module = module
        self._retries = timeout_policy.retries
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout_policy.seconds, transport=transport
        )

    def _headers_with_request_id(self, headers: dict[str, str] | None) -> dict[str, str]:
        merged = dict(headers or {})
        request_id = get_request_id()
        if request_id:
            merged["X-Request-ID"] = request_id
        return merged

    async def request(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, **kwargs: Any
    ) -> httpx.Response:
        merged_headers = self._headers_with_request_id(headers)

        last_error: Exception | None = None
        for _ in range(self._retries + 1):
            try:
                response = await self._client.request(method, url, headers=merged_headers, **kwargs)
            except httpx.TimeoutException as exc:
                last_error = exc
                continue
            except httpx.HTTPError as exc:
                last_error = exc
                continue
            if response.status_code >= 500:
                last_error = RuntimeError(f"{self._module} ตอบ HTTP {response.status_code}")
                continue
            return response

        raise Upstream502Error(
            f"โมดูล {self._module} ไม่ตอบสนองหรือขัดข้อง", details={"module": self._module}
        ) from last_error

    def stream(self, method: str, url: str, *, headers: dict[str, str] | None = None, **kwargs: Any):
        # แชต (03) ไม่ retry ตาม PLAN.md 3.3 — เรียกครั้งเดียวเป็น stream context manager
        merged_headers = self._headers_with_request_id(headers)
        return self._client.stream(method, url, headers=merged_headers, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()
