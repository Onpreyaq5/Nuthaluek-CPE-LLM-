from __future__ import annotations

from src.core.logging import get_logger

logger = get_logger(__name__)


class MockLogSink:
    async def send_batch(self, events: list[dict]) -> None:
        logger.info("mock_log_sink_batch", count=len(events))

    async def send_feedback(self, feedback: dict) -> None:
        logger.info("mock_log_sink_feedback")
