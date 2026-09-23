from __future__ import annotations

from src.core.config import get_settings
from src.schemas.chat import StudentPreferences
from src.schemas.plans import PlanValidateResponse
from src.schemas.students import GeneratedPlan

from ..http_base import HttpAdapterClient, raise_for_upstream
from ..interfaces import StudentContext

# ปลายทางของ 06 ยังไม่มีสัญญาจริง — PLACEHOLDER
PATH_VALIDATE = "/validate"
PATH_GENERATE = "/generate"


class HttpPlanEngine:
    async def validate(
        self, term: str, section_ids: list[str], student: StudentContext
    ) -> PlanValidateResponse:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.PLAN_ENGINE_URL, module="06", timeout_policy=settings.timeouts.validate_plan
        )
        try:
            response = await client.request(
                "POST",
                PATH_VALIDATE,
                json={
                    "term": term,
                    "section_ids": section_ids,
                    "student": student.model_dump(mode="json"),
                },
            )
        finally:
            await client.aclose()
        raise_for_upstream(response, "06")
        return PlanValidateResponse.model_validate(response.json())

    async def generate(
        self,
        term: str,
        preferences: StudentPreferences | None,
        student: StudentContext,
        must_include: list[str],
        exclude: list[str],
    ) -> list[GeneratedPlan]:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.PLAN_ENGINE_URL, module="06", timeout_policy=settings.timeouts.auto_plan
        )
        try:
            response = await client.request(
                "POST",
                PATH_GENERATE,
                json={
                    "term": term,
                    "preferences": preferences.model_dump(mode="json") if preferences else None,
                    "student": student.model_dump(mode="json"),
                    "must_include": must_include,
                    "exclude": exclude,
                },
            )
        finally:
            await client.aclose()
        raise_for_upstream(response, "06")
        items = response.json().get("plans", [])
        return [GeneratedPlan.model_validate(item) for item in items]
