from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from src.schemas.chat import (
    DoneEvent,
    ErrorEvent,
    SessionEvent,
    SourcesEvent,
    TokenEvent,
    ToolEndEvent,
    ToolStartEvent,
)

_EVENT_MODELS = {
    "session": SessionEvent,
    "tool_start": ToolStartEvent,
    "tool_end": ToolEndEvent,
    "token": TokenEvent,
    "sources": SourcesEvent,
    "done": DoneEvent,
    "error": ErrorEvent,
}


def format_sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def sanitize_event(raw: Any, tool_allowlist: set[str]) -> dict[str, Any] | None:
    """คืน event ที่ปลอดภัยจะส่งต่อให้หน้าเว็บ หรือ None ถ้าต้องทิ้ง

    - event ที่ไม่อยู่ในตาราง 6.2 หรือ schema ไม่ตรง -> ทิ้ง (None)
    - tool_start/tool_end ที่ tool ไม่อยู่ใน allowlist -> ทิ้ง
    - ผ่าน pydantic model เสมอ ทำให้ field แปลกปลอม (เช่น arguments) หลุดไปเองโดยอัตโนมัติ
    """
    if not isinstance(raw, dict):
        return None
    event_type = raw.get("type")
    model_cls = _EVENT_MODELS.get(event_type)
    if model_cls is None:
        return None
    try:
        model = model_cls.model_validate(raw)
    except ValidationError:
        return None
    if event_type in ("tool_start", "tool_end") and model.tool not in tool_allowlist:
        return None
    return model.model_dump()
