"""error 4xx จากโมดูลปลายทางต้องไม่กลายเป็น 500 ที่ผู้ใช้ไม่รู้ว่าผิดตรงไหน"""
from __future__ import annotations

import httpx
import pytest

from src.adapters.http_base import raise_for_upstream
from src.core.errors import NotFound404Error, Validation422Error


def _resp(status: int, body) -> httpx.Response:
    return httpx.Response(status, json=body)


def test_success_passes_through():
    raise_for_upstream(_resp(200, {"ok": True}), "06")


def test_not_found_keeps_upstream_message():
    with pytest.raises(NotFound404Error) as exc:
        raise_for_upstream(_resp(404, {"detail": "ไม่พบข้อมูลนักศึกษารหัส 6500000000"}), "05")
    assert "6500000000" in exc.value.message
    assert exc.value.details == {"module": "05", "upstream_status": 404}


def test_structured_detail_uses_its_message():
    # รูปแบบที่ 06 ตอบจริงตอนหา section ไม่เจอ
    body = {"detail": {"code": "SECTION_NOT_FOUND", "message": "Section 'X-01' not found", "section_id": "X-01"}}
    with pytest.raises(Validation422Error) as exc:
        raise_for_upstream(_resp(422, body), "06")
    assert exc.value.message == "Section 'X-01' not found"


def test_fastapi_validation_list_detail():
    body = {"detail": [{"loc": ["body", "term"], "msg": "Field required", "type": "missing"}]}
    with pytest.raises(Validation422Error) as exc:
        raise_for_upstream(_resp(422, body), "04")
    assert exc.value.message == "Field required"


def test_non_json_error_body():
    with pytest.raises(Validation422Error):
        raise_for_upstream(httpx.Response(400, text="bad request"), "04")
