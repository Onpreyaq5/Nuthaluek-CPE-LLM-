from __future__ import annotations

import re
from typing import Any

_STUDENT_IDS = [re.compile(r"\b\d{10}\b"), re.compile(r"\b\d{13}\b"), re.compile(r"\b\d{12}-\d\b")]
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE = re.compile(r"\b0\d{1,2}-?\d{3}-?\d{4}\b")
_SENSITIVE_KEYS = {
    "student_id", "name", "name_th", "name_en", "email", "phone", "password",
    "transcript", "jwt", "token", "access_token", "refresh_token", "secret",
    "api_key", "authorization", "cookie", "set-cookie",
}
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def is_probably_raw_student_id(value: str | None) -> bool:
    if not value:
        return False
    compact = value.replace("-", "")
    return compact.isdigit() and len(compact) in {10, 13}


def scrub_text(value: str) -> str:
    # Phone numbers are also ten digits, so classify them before student IDs.
    result = _BEARER.sub("Bearer [REDACTED]", value)
    result = _JWT.sub("[JWT]", result)
    result = _PHONE.sub("[PHONE]", result)
    for pattern in _STUDENT_IDS:
        result = pattern.sub("[STUDENT_ID]", result)
    result = _EMAIL.sub("[EMAIL]", result)
    return result


def scrub_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: scrub_payload(item)
            for key, item in value.items()
            if key.lower() not in _SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [scrub_payload(item) for item in value]
    if isinstance(value, str):
        return scrub_text(value)
    return value
