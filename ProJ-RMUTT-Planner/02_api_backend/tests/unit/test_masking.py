from __future__ import annotations

import random

from src.core.masking import hash_student_id, mask_payload, scrub_text


def _random_digits(n: int) -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(n))


def test_hash_student_id_deterministic_and_short() -> None:
    student_id = _random_digits(10)
    first = hash_student_id(student_id)
    second = hash_student_id(student_id)
    assert first == second
    assert len(first) == 16
    assert first != student_id


def test_scrub_text_masks_student_id_10_digits() -> None:
    student_id = _random_digits(10)
    text = f"รหัสนักศึกษาของฉันคือ {student_id} ครับ"
    scrubbed = scrub_text(text)
    assert student_id not in scrubbed
    assert "[รหัสนักศึกษา]" in scrubbed


def test_scrub_text_masks_student_id_13_digits() -> None:
    student_id = _random_digits(13)
    text = f"เลขบัตรประชาชน {student_id}"
    scrubbed = scrub_text(text)
    assert student_id not in scrubbed


def test_scrub_text_masks_student_id_with_dash() -> None:
    student_id = f"{_random_digits(12)}-{_random_digits(1)}"
    text = f"รหัส {student_id} นักศึกษา"
    scrubbed = scrub_text(text)
    assert student_id not in scrubbed


def test_scrub_text_masks_phone_number() -> None:
    phone = f"08{_random_digits(1)}-{_random_digits(3)}-{_random_digits(4)}"
    text = f"โทรหาที่ {phone} นะครับ"
    scrubbed = scrub_text(text)
    assert phone not in scrubbed
    assert "[เบอร์โทร]" in scrubbed


def test_scrub_text_masks_email() -> None:
    email = f"user{_random_digits(4)}@example.com"
    text = f"ติดต่อที่ {email}"
    scrubbed = scrub_text(text)
    assert email not in scrubbed
    assert "[อีเมล]" in scrubbed


def test_mask_payload_removes_sensitive_keys_including_nested() -> None:
    payload = {
        "name_th": "ทดสอบ ระบบ",
        "name_en": "Test System",
        "student_id": _random_digits(10),
        "password": "secret",
        "username": "admin",
        "term": "1/2569",
        "nested": {"student_id": _random_digits(10), "note": "ok"},
    }
    masked = mask_payload(payload)
    assert "name_th" not in masked
    assert "name_en" not in masked
    assert "student_id" not in masked
    assert "password" not in masked
    assert "username" not in masked
    assert masked["term"] == "1/2569"
    assert "student_id" not in masked["nested"]
    assert masked["nested"]["note"] == "ok"
