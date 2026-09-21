from __future__ import annotations

import json
from pathlib import Path

from src.schemas.students import ExplainResponse

from ..interfaces import StudentContext

_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


class MockExplainer:
    async def explain_plan(
        self, term: str, section_ids: list[str], student: StudentContext
    ) -> ExplainResponse:
        payload = json.loads((_FIXTURES_DIR / "plans" / "explain.success.json").read_text(encoding="utf-8"))
        return ExplainResponse.model_validate(payload["data"])
