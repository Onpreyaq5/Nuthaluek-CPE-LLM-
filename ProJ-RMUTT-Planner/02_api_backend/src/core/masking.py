from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

from src.core.config import get_settings

# ลำดับสำคัญ: ตรวจแบบมีขีด (12+1 หลัก) ก่อน แล้วจึงตรวจ 13 หลัก และ 10 หลัก
_STUDENT_ID_PATTERNS = [
    re.compile(r"\b\d{12}-\d{1}\b"),
    re.compile(r"\b\d{13}\b"),
    re.compile(r"\b\d{10}\b"),
]
_PHONE_PATTERN = re.compile(r"\b0\d{1,2}-?\d{3}-?\d{4}\b")
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

_MASKED_KEYS = {"name_th", "name_en", "student_id", "password", "username"}


def hash_student_id(student_id: str) -> str:
    secret = get_settings().JWT_SECRET.encode("utf-8")
    digest = hmac.new(secret, student_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:16]


def scrub_text(text: str) -> str:
    if not text:
        return text
    scrubbed = text
    for pattern in _STUDENT_ID_PATTERNS:
        scrubbed = pattern.sub("[รหัสนักศึกษา]", scrubbed)
    scrubbed = _PHONE_PATTERN.sub("[เบอร์โทร]", scrubbed)
    scrubbed = _EMAIL_PATTERN.sub("[อีเมล]", scrubbed)
    return scrubbed


def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in payload.items():
        if key in _MASKED_KEYS:
            continue
        if isinstance(value, dict):
            masked[key] = mask_payload(value)
        else:
            masked[key] = value
    return masked
