from __future__ import annotations

from src.adapters.mock.explainer import MockExplainer
from src.adapters.mock.log_sink import MockLogSink
from src.adapters.mock.student_data import MockStudentData


async def test_explain_plan_returns_thai_explanation() -> None:
    student = await MockStudentData().get_context("6500000000")
    result = await MockExplainer().explain_plan("1/2569", ["CPE301-01"], student)
    assert result.explanation
    assert result.sources


async def test_log_sink_accepts_batches_without_error() -> None:
    sink = MockLogSink()
    await sink.send_batch([{"event": "test"}])
    await sink.send_feedback({"feedback_id": 1})
