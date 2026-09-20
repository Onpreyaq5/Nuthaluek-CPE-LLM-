from __future__ import annotations

from src.adapters import get_course_catalog, get_explainer, get_log_sink, get_plan_engine, get_student_data
from src.adapters.mock.course_catalog import MockCourseCatalog
from src.adapters.mock.explainer import MockExplainer
from src.adapters.mock.log_sink import MockLogSink
from src.adapters.mock.plan_engine import MockPlanEngine
from src.adapters.mock.student_data import MockStudentData


def test_default_adapters_are_mock() -> None:
    assert isinstance(get_course_catalog(), MockCourseCatalog)
    assert isinstance(get_student_data(), MockStudentData)
    assert isinstance(get_plan_engine(), MockPlanEngine)
    assert isinstance(get_explainer(), MockExplainer)
    assert isinstance(get_log_sink(), MockLogSink)
