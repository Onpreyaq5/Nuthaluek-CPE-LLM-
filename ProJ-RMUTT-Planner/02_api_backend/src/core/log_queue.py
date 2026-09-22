from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from prometheus_client import Gauge

from src.core.logging import get_logger
from src.core.masking import mask_payload

logger = get_logger(__name__)

_MAX_QUEUE_SIZE = 1000
_FLUSH_INTERVAL_SECONDS = 2.0
_SHUTDOWN_FLUSH_TIMEOUT_SECONDS = 3.0

log_dropped_total_gauge = Gauge(
    "log_dropped_total", "จำนวนเหตุการณ์ log ที่ถูกทิ้งเพราะคิวเต็มหรือส่งให้ 08 ไม่สำเร็จ"
)


class LogQueue:
    """คิว log ในหน่วยความจำ ส่งเป็นชุดให้ adapter 08 ทุก _FLUSH_INTERVAL_SECONDS (PLAN.md หัวข้อ 7)

    เต็มหรือ 08 ล่ม -> ทิ้งเหตุการณ์นั้นและนับ log_dropped_total ไม่บล็อกผู้ใช้ (enqueue เป็น sync ล้วน)
    """

    def __init__(
        self,
        *,
        max_queue_size: int = _MAX_QUEUE_SIZE,
        flush_interval_seconds: float = _FLUSH_INTERVAL_SECONDS,
        shutdown_flush_timeout_seconds: float = _SHUTDOWN_FLUSH_TIMEOUT_SECONDS,
    ) -> None:
        self._queue: deque[dict[str, Any]] = deque()
        self._dropped_total = 0
        self._task: asyncio.Task | None = None
        self._max_queue_size = max_queue_size
        self._flush_interval_seconds = flush_interval_seconds
        self._shutdown_flush_timeout_seconds = shutdown_flush_timeout_seconds

    @property
    def dropped_total(self) -> int:
        return self._dropped_total

    @property
    def size(self) -> int:
        return len(self._queue)

    def enqueue(self, event: dict[str, Any]) -> None:
        if len(self._queue) >= self._max_queue_size:
            self._dropped_total += 1
            log_dropped_total_gauge.set(self._dropped_total)
            logger.warning("log_queue_full_dropped_event")
            return
        self._queue.append(mask_payload(event))

    async def _flush_once(self, log_sink) -> None:
        if not self._queue:
            return
        batch = list(self._queue)
        self._queue.clear()
        try:
            await log_sink.send_batch(batch)
        except Exception:
            self._dropped_total += len(batch)
            log_dropped_total_gauge.set(self._dropped_total)
            logger.warning("log_queue_flush_failed", count=len(batch))

    async def _run_forever(self, log_sink_factory) -> None:
        while True:
            await asyncio.sleep(self._flush_interval_seconds)
            await self._flush_once(log_sink_factory())

    def start(self, log_sink_factory) -> None:
        self._task = asyncio.create_task(self._run_forever(log_sink_factory))

    async def stop_and_flush(self, log_sink_factory) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        try:
            await asyncio.wait_for(
                self._flush_once(log_sink_factory()), timeout=self._shutdown_flush_timeout_seconds
            )
        except TimeoutError:
            logger.warning("log_queue_shutdown_flush_timeout")


_log_queue = LogQueue()


def get_log_queue() -> LogQueue:
    return _log_queue
