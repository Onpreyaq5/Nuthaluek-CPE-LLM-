from __future__ import annotations

import asyncio

from src.core.log_queue import LogQueue


class _RecordingLogSink:
    def __init__(self) -> None:
        self.batches: list[list[dict]] = []

    async def send_batch(self, events: list[dict]) -> None:
        self.batches.append(events)

    async def send_feedback(self, feedback: dict) -> None:
        pass


class _FailingLogSink:
    async def send_batch(self, events: list[dict]) -> None:
        raise ConnectionError("08 ล่ม")

    async def send_feedback(self, feedback: dict) -> None:
        raise ConnectionError("08 ล่ม")


def test_enqueue_masks_payload_before_storing() -> None:
    queue = LogQueue()
    queue.enqueue({"event": "test", "student_id": "6500000000", "id_hash": "abc123"})
    assert len(queue._queue) == 1
    stored = queue._queue[0]
    assert "student_id" not in stored
    assert stored["id_hash"] == "abc123"


def test_enqueue_drops_and_counts_when_queue_full() -> None:
    queue = LogQueue(max_queue_size=3)
    for i in range(3):
        queue.enqueue({"event": "filler", "i": i})
    assert queue.size == 3
    assert queue.dropped_total == 0

    queue.enqueue({"event": "overflow"})
    assert queue.size == 3
    assert queue.dropped_total == 1


def test_default_max_queue_size_is_1000() -> None:
    queue = LogQueue()
    for i in range(1000):
        queue.enqueue({"event": "filler", "i": i})
    assert queue.size == 1000

    queue.enqueue({"event": "overflow"})
    assert queue.size == 1000
    assert queue.dropped_total == 1


async def test_flush_once_sends_batch_and_clears_queue() -> None:
    queue = LogQueue()
    queue.enqueue({"event": "a"})
    queue.enqueue({"event": "b"})
    sink = _RecordingLogSink()

    await queue._flush_once(sink)

    assert queue.size == 0
    assert sink.batches == [[{"event": "a"}, {"event": "b"}]]


async def test_flush_once_does_nothing_when_queue_empty() -> None:
    queue = LogQueue()
    sink = _RecordingLogSink()

    await queue._flush_once(sink)

    assert sink.batches == []


async def test_flush_failure_counts_as_dropped() -> None:
    queue = LogQueue()
    queue.enqueue({"event": "a"})
    queue.enqueue({"event": "b"})
    sink = _FailingLogSink()

    await queue._flush_once(sink)

    assert queue.size == 0
    assert queue.dropped_total == 2


async def test_background_task_flushes_periodically() -> None:
    queue = LogQueue(flush_interval_seconds=0.01)
    sink = _RecordingLogSink()
    queue.enqueue({"event": "a"})

    try:
        queue.start(lambda: sink)
        await asyncio.sleep(0.05)
    finally:
        await queue.stop_and_flush(lambda: sink)

    assert sink.batches == [[{"event": "a"}]]


async def test_stop_and_flush_flushes_remaining_items_on_shutdown() -> None:
    queue = LogQueue()
    queue.enqueue({"event": "final"})
    sink = _RecordingLogSink()

    await queue.stop_and_flush(lambda: sink)

    assert sink.batches == [[{"event": "final"}]]
    assert queue.size == 0
