from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ChatMessage, ChatSession

_HISTORY_LIMIT = 10


async def create_session(db: AsyncSession, *, student_id: str, title: str | None) -> ChatSession:
    session = ChatSession(student_id=student_id, title=title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_message_by_id(db: AsyncSession, message_id: int) -> ChatMessage | None:
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    return result.scalar_one_or_none()


async def get_session_by_id(db: AsyncSession, session_id: int) -> ChatSession | None:
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    return result.scalar_one_or_none()


async def list_sessions_by_student(
    db: AsyncSession, *, student_id: str, offset: int, limit: int
) -> tuple[list[ChatSession], int]:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.student_id == student_id)
        .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
    )
    rows = list(result.scalars().all())
    return rows[offset : offset + limit], len(rows)


async def create_message(
    db: AsyncSession,
    *,
    session_id: int,
    role: str,
    content: str,
    status: str,
    sources: list[dict] | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session_id, role=role, content=content, status=status, sources=sources or []
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def update_message(
    db: AsyncSession,
    *,
    message_id: int,
    content: str,
    status: str,
    sources: list[dict] | None = None,
    latency_ms: int | None = None,
) -> None:
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    message = result.scalar_one()
    message.content = content
    message.status = status
    message.sources = sources or []
    message.latency_ms = latency_ms
    await db.commit()


async def get_recent_complete_messages(
    db: AsyncSession, *, session_id: int, exclude_message_id: int
) -> list[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.session_id == session_id,
            ChatMessage.status == "complete",
            ChatMessage.id != exclude_message_id,
        )
        .order_by(ChatMessage.id.desc())
        .limit(_HISTORY_LIMIT)
    )
    return list(reversed(result.scalars().all()))


async def list_messages_by_session(
    db: AsyncSession, *, session_id: int, offset: int, limit: int
) -> tuple[list[ChatMessage], int]:
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id.asc())
    )
    rows = list(result.scalars().all())
    return rows[offset : offset + limit], len(rows)
