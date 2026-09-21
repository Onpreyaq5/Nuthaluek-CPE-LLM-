from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from src.adapters import get_answer_generator, get_chat_router, get_student_data
from src.adapters.interfaces import AnswerGenerator, ChatRouter, StudentData
from src.api.deps import CurrentUser, current_user
from src.core.config import get_settings
from src.core.db import get_db
from src.core.envelope import success_envelope
from src.core.errors import Upstream502Error
from src.core.log_queue import get_log_queue
from src.core.masking import scrub_text
from src.core.middleware import get_request_id
from src.core.pagination import decode_cursor, encode_cursor
from src.core.sse import format_sse, sanitize_event
from src.schemas.chat import (
    ChatHistoryItem,
    ChatMessageListResponse,
    ChatRequest,
    ChatSessionListResponse,
    ChatSessionSummary,
    EnrichedChatRequest,
    EnrichedStudent,
)
from src.schemas.chat import ChatMessage as ChatMessageSchema
from src.schemas.envelope import SuccessEnvelope
from src.services import chat_orchestrator, chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

_UPSTREAM_START_FAIL_MESSAGE = "โมดูล Router (03) ไม่ตอบสนอง"
_UPSTREAM_MIDSTREAM_MESSAGE = "โมดูล Router (03) หยุดตอบสนองกลางทาง"


async def _prepend(first: dict, rest: AsyncIterator[dict]) -> AsyncIterator[dict]:
    """ใส่ event ที่ peek ไปแล้วคืนเข้า stream ก่อนอ่านต่อจากตัวเดิม (ไม่เสีย event แรกที่ดึงมาเช็คแล้วว่า
    03 ตอบสนองจริง)"""
    yield first
    async for item in rest:
        yield item


@router.post("")
async def chat(
    payload: ChatRequest,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    student_data: StudentData = Depends(get_student_data),
    chat_router_adapter: ChatRouter = Depends(get_chat_router),
    answer_generator: AnswerGenerator = Depends(get_answer_generator),
) -> StreamingResponse:
    settings = get_settings()
    request_id = get_request_id()

    session = await chat_service.resolve_session(
        db, session_id=payload.session_id, student_id=user.student_id, initial_message=payload.message
    )
    user_message = await chat_service.save_user_message(
        db, session_id=session.id, content=payload.message
    )
    history_items = await chat_service.build_history(
        db, session_id=session.id, exclude_message_id=user_message.id
    )
    student_context = await student_data.get_context(user.student_id)

    scrubbed_query = scrub_text(payload.message)
    enriched = EnrichedChatRequest(
        request_id=request_id,
        session_id=session.id,
        query=scrubbed_query,
        student=EnrichedStudent(
            id_hash=user.id_hash,
            program_id=student_context.program_id,
            curriculum_year=student_context.curriculum_year,
            year_level=student_context.year_level,
            credits_earned=student_context.credits_earned,
            preferences=student_context.preferences,
        ),
        history=[ChatHistoryItem(**item) for item in history_items],
        plan_draft=payload.plan_draft,
        term=settings.CURRENT_TERM,
    )

    # chat_router_adapter.stream() คืน "internal event" ของ router เท่านั้น (key "kind") —
    # chat_orchestrator เป็นตัวตัดสินว่าจะเรียก answer_generator (07) ไหม แล้วผลิต public event
    # (key "type") ที่ปลอดภัยจะส่งต่อ frontend ผ่าน sanitize_event เท่านั้น ห้าม forward event ภายในตรงๆ
    router_events: AsyncIterator[dict] = chat_router_adapter.stream(enriched)

    # ก่อนเริ่ม stream จริง: peek เฉพาะฝั่ง router (03) เท่านั้น — ถ้า 03 ไม่ตอบภายใน chat_start timeout
    # หรือพังทันที -> HTTP 502 ปกติ (ไม่ใช่ SSE) ต้อง peek "ก่อน" เข้า orchestrator เสมอ ไม่งั้นความล้มเหลว
    # ของ 07 (answer_generator ยังไม่พร้อม) ที่เกิดขึ้นทันทีสำหรับ intent ที่ไม่มี tool เลย (เช่น GENERAL_CHAT)
    # จะถูกเข้าใจผิดว่าเป็น "03 ไม่ตอบสนอง" ทั้งที่ 03 ตอบมาถูกต้องแล้ว
    try:
        first_router_event = await asyncio.wait_for(
            router_events.__anext__(), timeout=settings.timeouts.chat_start.seconds
        )
    except Exception as exc:
        await router_events.aclose()
        raise Upstream502Error(_UPSTREAM_START_FAIL_MESSAGE, details={"module": "03"}) from exc

    orchestrated: AsyncIterator[dict] = chat_orchestrator.run_chat_turn(
        _prepend(first_router_event, router_events),
        answer_generator,
        question=scrubbed_query,
        history=history_items,
    )

    assistant_message = await chat_service.start_assistant_message(db, session_id=session.id)
    tool_allowlist = settings.tool_allowlist_set
    started_at = time.monotonic()
    chat_total_seconds = settings.timeouts.chat_total.seconds
    chat_idle_seconds = settings.timeouts.chat_idle.seconds

    async def event_stream() -> AsyncIterator[str]:
        tokens: list[str] = []
        sources_payload: list[dict] = []
        message_status = "interrupted"
        latency_ms: int | None = None

        yield format_sse({"type": "session", "session_id": session.id})

        try:
            while True:
                elapsed = time.monotonic() - started_at
                remaining_total = chat_total_seconds - elapsed
                if remaining_total <= 0:
                    raise TimeoutError("chat total timeout exceeded")
                idle_timeout = min(chat_idle_seconds, remaining_total)
                current = await asyncio.wait_for(orchestrated.__anext__(), timeout=idle_timeout)

                raw = dict(current)
                if raw.get("type") == "done":
                    # message_id ต้องเป็นแถวจริงที่บันทึกไว้ใน DB ของ 02 เท่านั้น ไม่ใช่ค่าจาก 03/07
                    raw["message_id"] = assistant_message.id
                sanitized = sanitize_event(raw, tool_allowlist)
                if sanitized is not None and sanitized["type"] != "session":
                    # อัปเดตสถานะที่ต้อง persist "ก่อน" yield เสมอ: ถ้าถูก cancel พอดีตอน yield
                    # (client ตัดการเชื่อมต่อ) ข้อมูลที่ส่งออกไปแล้วต้องถูกบันทึกไว้ ไม่ใช่หายไป
                    event_type = sanitized["type"]
                    if event_type == "token":
                        tokens.append(sanitized["text"])
                    elif event_type == "sources":
                        sources_payload = sanitized["items"]
                    elif event_type == "done":
                        message_status = "complete"
                        latency_ms = int((time.monotonic() - started_at) * 1000)
                    yield format_sse(sanitized)
                    if event_type in ("done", "error"):
                        break
        except StopAsyncIteration:
            if message_status != "complete":
                yield format_sse(
                    {"type": "error", "code": "UPSTREAM_502", "message": _UPSTREAM_MIDSTREAM_MESSAGE}
                )
        except asyncio.CancelledError:
            await chat_service.finish_assistant_message(
                db,
                message_id=assistant_message.id,
                content="".join(tokens),
                status="cancelled",
                sources=sources_payload,
            )
            get_log_queue().enqueue(
                {
                    "event": "chat_message",
                    "id_hash": user.id_hash,
                    "session_id": session.id,
                    "status": "cancelled",
                }
            )
            raise
        except Exception:
            yield format_sse(
                {"type": "error", "code": "UPSTREAM_502", "message": _UPSTREAM_MIDSTREAM_MESSAGE}
            )
        finally:
            # ปิด orchestrator generator เสมอ (cascade ไปปิด router_events/answer_generator ที่ยังค้างอยู่
            # ด้วยกลไก async-for delegation ของ Python) ไม่ว่าจะจบแบบไหนก็ตาม
            await orchestrated.aclose()

        await chat_service.finish_assistant_message(
            db,
            message_id=assistant_message.id,
            content="".join(tokens),
            status=message_status,
            sources=sources_payload,
            latency_ms=latency_ms,
        )
        # log ไป 08 แบบไม่บล็อกผู้ใช้ผ่านคิว — ไม่มีเนื้อข้อความเลย มีแค่ metadata
        get_log_queue().enqueue(
            {
                "event": "chat_message",
                "id_hash": user.id_hash,
                "session_id": session.id,
                "status": message_status,
            }
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/sessions", response_model=SuccessEnvelope[ChatSessionListResponse])
async def list_chat_sessions(
    cursor: str | None = None,
    limit: int = 20,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    offset = decode_cursor(cursor)
    sessions, total = await chat_service.list_sessions(
        db, student_id=user.student_id, offset=offset, limit=limit
    )
    next_offset = offset + limit
    next_cursor = encode_cursor(next_offset) if next_offset < total else None
    data = ChatSessionListResponse(
        items=[
            ChatSessionSummary(id=s.id, title=s.title, updated_at=s.updated_at) for s in sessions
        ],
        next_cursor=next_cursor,
    )
    return success_envelope(data.model_dump(mode="json"))


@router.get("/sessions/{session_id}/messages", response_model=SuccessEnvelope[ChatMessageListResponse])
async def list_chat_messages(
    session_id: int,
    cursor: str | None = None,
    limit: int = 20,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    offset = decode_cursor(cursor)
    messages, total = await chat_service.list_messages(
        db, session_id=session_id, student_id=user.student_id, offset=offset, limit=limit
    )
    next_offset = offset + limit
    next_cursor = encode_cursor(next_offset) if next_offset < total else None
    data = ChatMessageListResponse(
        items=[
            ChatMessageSchema(
                id=m.id, role=m.role, content=m.content, status=m.status,
                sources=m.sources, created_at=m.created_at,
            )
            for m in messages
        ],
        next_cursor=next_cursor,
    )
    return success_envelope(data.model_dump(mode="json"))
