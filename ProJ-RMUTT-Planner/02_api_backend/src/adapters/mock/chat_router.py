from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from src.schemas.chat import EnrichedChatRequest

_TOKENS = ["ถอนรายวิชา", "ได้ตามระเบียบข้อ 18", " ของมหาวิทยาลัยครับ"]
_FAIL_MARKER = "__fail__"


class MockChatRouter:
    async def stream(self, enriched: EnrichedChatRequest) -> AsyncIterator[dict]:
        yield {"type": "session", "session_id": enriched.session_id}
        await asyncio.sleep(0.01)
        yield {"type": "tool_start", "tool": "search_knowledge"}
        await asyncio.sleep(0.01)
        yield {"type": "tool_end", "tool": "search_knowledge"}

        if _FAIL_MARKER in enriched.query:
            await asyncio.sleep(0.01)
            raise ConnectionError("จำลอง 03 ล่มกลางทาง")

        for token in _TOKENS:
            await asyncio.sleep(0.01)
            yield {"type": "token", "text": token}

        yield {
            "type": "sources",
            "items": [
                {
                    "title": "ข้อบังคับฯ",
                    "section": "ข้อ 18",
                    "page": 12,
                    "document_id": "doc-regulation-2566",
                    "url": None,
                }
            ],
        }
        await asyncio.sleep(0.01)
        yield {"type": "done", "message_id": 301}
