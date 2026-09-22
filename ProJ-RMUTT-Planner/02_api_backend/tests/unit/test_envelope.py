from __future__ import annotations

from src.core.envelope import error_envelope, success_envelope
from src.core.middleware import request_context


def test_success_envelope_shape() -> None:
    with request_context("req_test123"):
        envelope = success_envelope({"foo": "bar"})

    assert envelope["ok"] is True
    assert envelope["data"] == {"foo": "bar"}
    assert envelope["meta"]["request_id"] == "req_test123"
    assert isinstance(envelope["meta"]["took_ms"], float)


def test_error_envelope_shape() -> None:
    with request_context("req_test456"):
        envelope = error_envelope("VALIDATION_422", "ข้อมูลผิด", {"field": "term"})

    assert envelope["ok"] is False
    assert envelope["error"] == {
        "code": "VALIDATION_422",
        "message": "ข้อมูลผิด",
        "details": {"field": "term"},
    }
    assert envelope["meta"]["request_id"] == "req_test456"


def test_error_envelope_defaults_details_to_empty_dict() -> None:
    with request_context("req_test789"):
        envelope = error_envelope("NOT_FOUND_404", "ไม่พบข้อมูล")

    assert envelope["error"]["details"] == {}
