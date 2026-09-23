from __future__ import annotations

from src.core.config import get_settings
from src.schemas.plans import PlanValidateResponse
from src.schemas.students import ExplainResponse

from ..http_base import HttpAdapterClient, raise_for_upstream
from ..interfaces import StudentContext

# ปลายทางของ 07 ยังไม่มีสัญญาจริง — PLACEHOLDER
PATH_EXPLAIN = "/explain"


class HttpExplainer:
    async def explain_plan(
        self,
        term: str,
        section_ids: list[str],
        student: StudentContext,
        validation: PlanValidateResponse | None = None,
    ) -> ExplainResponse:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.EXPLAINER_URL, module="07", timeout_policy=settings.timeouts.write
        )
        try:
            response = await client.request(
                "POST",
                PATH_EXPLAIN,
                json={
                    "term": term,
                    "section_ids": section_ids,
                    "student": student.model_dump(mode="json"),
                    "conflicts": (
                        [c.model_dump(mode="json") for c in validation.conflicts] if validation else None
                    ),
                    "warnings": (
                        [w.model_dump(mode="json") for w in validation.warnings] if validation else None
                    ),
                },
            )
        finally:
            await client.aclose()
        raise_for_upstream(response, "07")
        return ExplainResponse.model_validate(response.json())
