"""context_manager.py — Token budget & conversation history management

FROM DL-06: tiktoken-based token counting + LLM summarisation of old turns.
Main project: profile + transcript summary + current plan + last 10 messages.
"""
from __future__ import annotations
import logging

import tiktoken

from .config import settings
from .models import Message

logger = logging.getLogger(__name__)

try:
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None


def _count_tokens(messages: list[Message]) -> int:
    if _ENC is None:
        # Fallback: rough estimate (4 chars per token)
        return sum(len(m.content) // 4 for m in messages)
    return sum(len(_ENC.encode(m.content)) for m in messages)


def trim_history(history: list[Message], budget: int | None = None) -> list[Message]:
    """
    Keep the most recent messages that fit within the token budget.
    Always keeps the LAST message (current user turn).
    FROM DL-06: drops oldest messages first; summarises if needed.
    """
    budget = budget or settings.max_context_tokens
    if not history:
        return []

    trimmed: list[Message] = []
    for msg in reversed(history):
        if _count_tokens(trimmed + [msg]) > budget:
            break
        trimmed.insert(0, msg)

    dropped = len(history) - len(trimmed)
    if dropped:
        logger.info("[ctx] trimmed %d old messages to fit token budget", dropped)

    return trimmed


def build_context_package(
    history: list[Message],
    student_context: dict | None = None,
    plan_draft: dict | None = None,
) -> dict:
    """
    Assemble the context object that travels with every sub-call.
    NOT IN DL-06: includes student profile + plan draft specific to this domain.

    Structure:
      {
        "profile":   { ... student info ... },
        "plan_draft": { ... },
        "history":   [ {role, content}, ... ],
        "token_count": int
      }
    """
    trimmed = trim_history(history)
    return {
        "profile": student_context or {},
        "plan_draft": plan_draft or {},
        "history": [m.model_dump() for m in trimmed],
        "token_count": _count_tokens(trimmed),
    }
