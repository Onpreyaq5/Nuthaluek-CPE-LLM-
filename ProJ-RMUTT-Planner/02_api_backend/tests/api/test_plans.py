from __future__ import annotations

import httpx
import pytest

from src.adapters import get_explainer, get_plan_engine
from src.core.errors import Upstream502Error
from src.main import app
from src.schemas.plans import ConflictItem, PlanValidateResponse, ValidateSummary
from src.schemas.students import ExplainResponse

pytestmark = pytest.mark.db


class _FailingPlanEngine:
    async def validate(self, term, section_ids, student):
        raise Upstream502Error("โมดูลตรวจตารางชน (06) ไม่ตอบสนอง", details={"module": "06"})

    async def generate(self, *args, **kwargs):
        raise Upstream502Error("โมดูลตรวจตารางชน (06) ไม่ตอบสนอง", details={"module": "06"})


class _FailingExplainer:
    async def explain_plan(self, term, section_ids, student, validation=None):
        raise Upstream502Error("โมดูลอธิบายแผน (07) ไม่ตอบสนอง", details={"module": "07"})


class _ConflictPlanEngine:
    """จำลอง 06 ตอบกลับมาว่าแผนนี้ชนจริง — ใช้ยืนยันว่า explain_plan() เรียก plan_engine.validate()
    จริงก่อนส่งต่อให้ 07 (บั๊กเดิม: ไม่เคยเรียกเลย ทำให้ 07 verdict "unknown" เสมอ)"""

    async def validate(self, term, section_ids, student):
        return PlanValidateResponse(
            conflicts=[
                ConflictItem(
                    type="TIME_OVERLAP",
                    message="เวลาเรียนชนกัน",
                    section_ids=section_ids,
                    code="C1_TIME_OVERLAP",
                    severity="ERROR",
                    message_th="เวลาเรียนชนกัน",
                    message_en="Time overlap",
                )
            ],
            warnings=[],
            summary=ValidateSummary(total_credits=3, section_count=len(section_ids), is_valid=False),
        )

    async def generate(self, *args, **kwargs):
        raise NotImplementedError


class _CapturingExplainer:
    def __init__(self) -> None:
        self.received_validation: PlanValidateResponse | None | str = "__not_called__"

    async def explain_plan(self, term, section_ids, student, validation=None) -> ExplainResponse:
        self.received_validation = validation
        return ExplainResponse(explanation="คำอธิบายจำลอง", sources=[])


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


async def test_validate_no_conflicts(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.post(
        "/api/v1/plans/validate", json={"term": "1/2569", "section_ids": ["CPE301-02", "GE101-01"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["conflicts"] == []
    assert body["data"]["summary"]["is_valid"] is True


async def test_validate_time_overlap_c1(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.post(
        "/api/v1/plans/validate", json={"term": "1/2569", "section_ids": ["CPE201-01", "CPE301-01"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert any(c["type"] == "TIME_OVERLAP" for c in body["data"]["conflicts"])


async def test_validate_prerequisite_missing_c3(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.post(
        "/api/v1/plans/validate", json={"term": "1/2569", "section_ids": ["CPE401-01"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert any(c["type"] == "PREREQUISITE_MISSING" for c in body["data"]["conflicts"])


async def test_validate_section_not_found_returns_404(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.post(
        "/api/v1/plans/validate", json={"term": "1/2569", "section_ids": ["NOT-EXIST"]}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND_404"
    assert response.json()["error"]["details"]["section_ids"] == ["NOT-EXIST"]


async def test_validate_upstream_down_returns_502(logged_in_client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_plan_engine] = lambda: _FailingPlanEngine()
    response = await logged_in_client.post(
        "/api/v1/plans/validate", json={"term": "1/2569", "section_ids": ["CPE301-02"]}
    )
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_502"


async def test_validate_empty_section_ids_returns_422(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.post(
        "/api/v1/plans/validate", json={"term": "1/2569", "section_ids": []}
    )
    assert response.status_code == 422


async def test_validate_too_many_section_ids_returns_422(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.post(
        "/api/v1/plans/validate", json={"term": "1/2569", "section_ids": [f"S-{i}" for i in range(16)]}
    )
    assert response.status_code == 422


async def test_save_read_list_delete_plan_flow(logged_in_client: httpx.AsyncClient) -> None:
    create_response = await logged_in_client.post(
        "/api/v1/plans",
        json={"term": "1/2569", "name": "แผนทดสอบ", "section_ids": ["CPE301-02", "GE101-01"]},
    )
    assert create_response.status_code == 200
    plan_id = create_response.json()["data"]["plan_id"]

    list_response = await logged_in_client.get("/api/v1/plans", params={"term": "1/2569"})
    assert list_response.status_code == 200
    assert any(p["id"] == plan_id for p in list_response.json()["data"]["items"])

    detail_response = await logged_in_client.get(f"/api/v1/plans/{plan_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["name"] == "แผนทดสอบ"
    assert {s["section_id"] for s in detail["sections"]} == {"CPE301-02", "GE101-01"}

    delete_response = await logged_in_client.delete(f"/api/v1/plans/{plan_id}")
    assert delete_response.status_code == 200

    after_delete = await logged_in_client.get(f"/api/v1/plans/{plan_id}")
    assert after_delete.status_code == 404


async def test_create_plan_duplicate_name_returns_409(logged_in_client: httpx.AsyncClient) -> None:
    payload = {"term": "1/2569", "name": "แผนซ้ำ", "section_ids": ["CPE301-02"]}
    first = await logged_in_client.post("/api/v1/plans", json=payload)
    assert first.status_code == 200

    second = await logged_in_client.post("/api/v1/plans", json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT_409"


async def test_get_and_delete_other_students_plan_returns_403(
    logged_in_client: httpx.AsyncClient, second_student: dict
) -> None:
    create_response = await logged_in_client.post(
        "/api/v1/plans", json={"term": "1/2569", "name": "แผนของฉัน", "section_ids": ["GE101-01"]}
    )
    plan_id = create_response.json()["data"]["plan_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", cookies={"session": second_student["token"]}
    ) as other_client:
        get_response = await other_client.get(f"/api/v1/plans/{plan_id}")
        delete_response = await other_client.delete(f"/api/v1/plans/{plan_id}")

    assert get_response.status_code == 403
    assert get_response.json()["error"]["code"] == "FORBIDDEN_403"
    assert delete_response.status_code == 403
    assert delete_response.json()["error"]["code"] == "FORBIDDEN_403"


async def test_get_nonexistent_plan_returns_404(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.get("/api/v1/plans/999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND_404"


async def test_auto_plan_returns_explained_plans(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.post("/api/v1/plans/auto", json={"term": "1/2569"})

    assert response.status_code == 200
    plans = response.json()["data"]["plans"]
    assert len(plans) == 3
    assert all(p["explanation"] for p in plans)


async def test_auto_plan_ignores_request_preferences_uses_db(logged_in_client: httpx.AsyncClient) -> None:
    # ส่ง preferences ที่ขัดกับของใน DB มาด้วย (max_credits สูงลิ่ว) ต้องไม่มีผลอะไรเลย
    response = await logged_in_client.post(
        "/api/v1/plans/auto",
        json={
            "term": "1/2569",
            "preferences": {"free_days": [], "no_early_class": False, "max_credits": 999},
        },
    )
    assert response.status_code == 200
    plans = response.json()["data"]["plans"]
    # preferences ของ DB (seed) จำกัด max_credits ไว้ที่ 21 — ถ้า endpoint เผลอใช้ preferences จาก
    # request (999) แทน จะได้แผนที่หน่วยกิตรวมเกิน 21 ซึ่งไม่ควรเกิดขึ้น
    assert all(p["total_credits"] <= 21 for p in plans)


async def test_auto_plan_explainer_down_returns_plan_with_null_explanation_and_warning(
    logged_in_client: httpx.AsyncClient,
) -> None:
    app.dependency_overrides[get_explainer] = lambda: _FailingExplainer()
    response = await logged_in_client.post("/api/v1/plans/auto", json={"term": "1/2569"})

    assert response.status_code == 200  # ไม่ล้มทั้ง request แม้ 07 จะล่ม
    plans = response.json()["data"]["plans"]
    assert len(plans) == 3
    assert all(p["explanation"] is None for p in plans)
    assert all(any("07" in w for w in p["warnings"]) for p in plans)


async def test_auto_plan_without_login_returns_401() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/plans/auto", json={"term": "1/2569"})
    assert response.status_code == 401


async def test_explain_plan_calls_plan_engine_validate_and_forwards_conflicts_to_explainer(
    logged_in_client: httpx.AsyncClient,
) -> None:
    """เคสที่เคย fail: explain_plan() ไม่เคยเรียก plan_engine.validate() (06) เลย ทำให้ 07 ไม่มีทาง
    ตอบ verdict ตามจริงได้ — ตอนนี้ต้องเรียกเสมอ และ validation ที่ส่งต่อต้องมี conflict จริงจาก 06"""
    create_response = await logged_in_client.post(
        "/api/v1/plans", json={"term": "1/2569", "name": "แผนตรวจ conflict", "section_ids": ["GE101-01"]}
    )
    plan_id = create_response.json()["data"]["plan_id"]

    capturing = _CapturingExplainer()
    app.dependency_overrides[get_plan_engine] = lambda: _ConflictPlanEngine()
    app.dependency_overrides[get_explainer] = lambda: capturing

    response = await logged_in_client.get(f"/api/v1/plans/{plan_id}/explain")

    assert response.status_code == 200
    assert capturing.received_validation != "__not_called__"
    assert capturing.received_validation is not None
    assert len(capturing.received_validation.conflicts) == 1
    assert capturing.received_validation.conflicts[0].type == "TIME_OVERLAP"
    assert capturing.received_validation.conflicts[0].code == "C1_TIME_OVERLAP"
    assert capturing.received_validation.summary.is_valid is False


async def test_auto_plan_forwards_no_conflict_validation_to_explainer_not_none(
    logged_in_client: httpx.AsyncClient,
) -> None:
    """เคสเดียวกันแต่ฝั่ง /plans/auto: แผนจาก 06.generate() ผ่าน hard constraint มาแล้ว แต่ก่อนหน้านี้ก็ยัง
    ไม่เคยส่ง validation อะไรให้ 07 เลยสักครั้ง (ไม่ใช่แค่ conflicts เปล่าๆ แต่ไม่ส่งอะไรไปเลย/None)"""
    capturing = _CapturingExplainer()
    app.dependency_overrides[get_explainer] = lambda: capturing

    response = await logged_in_client.post("/api/v1/plans/auto", json={"term": "1/2569"})

    assert response.status_code == 200
    assert capturing.received_validation != "__not_called__"
    assert capturing.received_validation is not None
    assert capturing.received_validation.conflicts == []
    assert capturing.received_validation.summary.is_valid is True


async def test_explain_plan_success(logged_in_client: httpx.AsyncClient) -> None:
    create_response = await logged_in_client.post(
        "/api/v1/plans", json={"term": "1/2569", "name": "แผนขอคำอธิบาย", "section_ids": ["GE101-01"]}
    )
    plan_id = create_response.json()["data"]["plan_id"]

    response = await logged_in_client.get(f"/api/v1/plans/{plan_id}/explain")

    assert response.status_code == 200
    assert response.json()["data"]["explanation"]


async def test_explain_nonexistent_plan_returns_404(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.get("/api/v1/plans/999999/explain")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND_404"


async def test_explain_other_students_plan_returns_403(
    logged_in_client: httpx.AsyncClient, second_student: dict
) -> None:
    create_response = await logged_in_client.post(
        "/api/v1/plans", json={"term": "1/2569", "name": "แผนส่วนตัว", "section_ids": ["GE101-01"]}
    )
    plan_id = create_response.json()["data"]["plan_id"]

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", cookies={"session": second_student["token"]}
    ) as other_client:
        response = await other_client.get(f"/api/v1/plans/{plan_id}/explain")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_403"
