from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import Forbidden403Error, NotFound404Error
from src.core.masking import scrub_text
from src.models import ChatMessage, ChatSession
from src.repositories import chat_repository

_SESSION_NOT_FOUND_MESSAGE = "ไม่พบบทสนทนานี้"
_SESSION_FORBIDDEN_MESSAGE = "ไม่มีสิทธิ์เข้าถึงบทสนทนานี้"
_TITLE_MAX_LENGTH = 60


async def get_owned_session(db: AsyncSession, *, session_id: int, student_id: str) -> ChatSession:
    session = await chat_repository.get_session_by_id(db, session_id)
    if session is None:
        raise NotFound404Error(_SESSION_NOT_FOUND_MESSAGE, details={"session_id": session_id})
    if session.student_id != student_id:
        raise Forbidden403Error(_SESSION_FORBIDDEN_MESSAGE, details={"session_id": session_id})
    return session


async def resolve_session(
    db: AsyncSession, *, session_id: int | None, student_id: str, initial_message: str
) -> ChatSession:
    if session_id is None:
        title = initial_message[:_TITLE_MAX_LENGTH]
        return await chat_repository.create_session(db, student_id=student_id, title=title)
    return await get_owned_session(db, session_id=session_id, student_id=student_id)


async def save_user_message(db: AsyncSession, *, session_id: int, content: str) -> ChatMessage:
    return await chat_repository.create_message(
        db, session_id=session_id, role="user", content=content, status="complete"
    )


async def start_assistant_message(db: AsyncSession, *, session_id: int) -> ChatMessage:
    return await chat_repository.create_message(
        db, session_id=session_id, role="assistant", content="", status="interrupted"
    )


async def finish_assistant_message(
    db: AsyncSession,
    *,
    message_id: int,
    content: str,
    status: str,
    sources: list[dict] | None = None,
    latency_ms: int | None = None,
) -> None:
    await chat_repository.update_message(
        db, message_id=message_id, content=content, status=status, sources=sources, latency_ms=latency_ms
    )


async def build_history(
    db: AsyncSession, *, session_id: int, exclude_message_id: int
) -> list[dict[str, str]]:
    recent = await chat_repository.get_recent_complete_messages(
        db, session_id=session_id, exclude_message_id=exclude_message_id
    )
    return [{"role": m.role, "content": scrub_text(m.content)} for m in recent]


async def list_sessions(
    db: AsyncSession, *, student_id: str, offset: int, limit: int
) -> tuple[list[ChatSession], int]:
    return await chat_repository.list_sessions_by_student(
        db, student_id=student_id, offset=offset, limit=limit
    )


async def list_messages(
    db: AsyncSession, *, session_id: int, student_id: str, offset: int, limit: int
) -> tuple[list[ChatMessage], int]:
    await get_owned_session(db, session_id=session_id, student_id=student_id)
    return await chat_repository.list_messages_by_session(
        db, session_id=session_id, offset=offset, limit=limit
    )
