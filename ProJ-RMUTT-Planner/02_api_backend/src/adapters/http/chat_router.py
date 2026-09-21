from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from src.core.config import get_settings
from src.schemas.chat import EnrichedChatRequest

from ..http_base import HttpAdapterClient

# ปลายทางของ 03 ยังไม่มีสัญญาจริง — PLACEHOLDER
# หมายเหตุ: httpx.aiter_lines()/aiter_text() ใช้ incremental decoder ของ UTF-8 อยู่แล้วภายใน (ผ่าน
# codecs incremental decoder) จึงกัน token ภาษาไทยขาดตอนข้าม chunk ให้อัตโนมัติ — ยืนยันด้วย
# tests/unit/test_http_chat_router.py
PATH_STREAM = "/chat/stream"


class HttpChatRouter:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def stream(self, enriched: EnrichedChatRequest) -> AsyncIterator[dict]:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.ROUTER_URL,
            module="03",
            timeout_policy=settings.timeouts.chat_total,
            transport=self._transport,
        )
        try:
            async with client.stream(
                "POST", PATH_STREAM, json=enriched.model_dump(mode="json")
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    yield json.loads(line[len("data: ") :])
        finally:
            await client.aclose()
