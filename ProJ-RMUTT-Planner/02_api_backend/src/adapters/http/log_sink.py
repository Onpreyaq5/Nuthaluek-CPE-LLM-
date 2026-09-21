from __future__ import annotations

from src.core.config import get_settings

from ..http_base import HttpAdapterClient

# ปลายทางของ 08 ยังไม่มีสัญญาจริง — PLACEHOLDER
PATH_EVENTS_BATCH = "/events/batch"
PATH_FEEDBACK = "/feedback"


class HttpLogSink:
    async def send_batch(self, events: list[dict]) -> None:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.LOG_SINK_URL, module="08", timeout_policy=settings.timeouts.write
        )
        try:
            await client.request("POST", PATH_EVENTS_BATCH, json={"events": events})
        finally:
            await client.aclose()

    async def send_feedback(self, feedback: dict) -> None:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.LOG_SINK_URL, module="08", timeout_policy=settings.timeouts.write
        )
        try:
            await client.request("POST", PATH_FEEDBACK, json=feedback)
        finally:
            await client.aclose()
