"""models.py — Pydantic schemas for Module 03 AI Router / Agent

Input  : RouterRequest  (from Module 02 API/Backend)
Output : RouterResponse (to Module 07 RAG/LLM Engine)
"""
from __future__ import annotations
from typing import Any, List, Optional, ClassVar, Literal
from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────
#  Inbound (from Module 02)
# ──────────────────────────────────────────────────────────────

class Message(BaseModel):
    """One turn in conversation history."""
    role: str                   # "user" | "assistant" | "tool"
    content: str

class StudentPreferences(BaseModel):
    free_days: List[Literal["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]] = Field(default_factory=list)
    no_early_class: bool = False
    max_credits: Optional[int] = None

class RouterRequest(BaseModel):
    """Payload that Module 02 (API/Backend) sends to the router."""
    request_id: Optional[str] = None
    student_id: str             # synthetic_hash_only
    session_id: str
    message: str
    history: List[Message] = Field(default_factory=list)
    plan_draft: Optional[dict] = None   # draft plan if user is mid-session
    term: Optional[str] = None
    preferences: StudentPreferences = Field(default_factory=StudentPreferences)


# ──────────────────────────────────────────────────────────────
#  Intent & Slots  (internal)
# ──────────────────────────────────────────────────────────────

class Slots(BaseModel):
    """Extracted slot values from the user query."""
    term: Optional[str] = None              # e.g. "1/2569"
    academic_year: Optional[int] = None     # e.g. 2569
    course_codes: List[str] = Field(default_factory=list)  # e.g. ["CPE101"]
    day: Optional[str] = None              # e.g. "จันทร์"
    time_str: Optional[str] = None         # e.g. "09:00"
    topic: Optional[str] = None            # free-text topic for RAG


class ClassificationResult(BaseModel):
    """Output of the intent classifier (Layer 1 keyword or Layer 2 LLM)."""
    intent: str               # one of the 6 intents below
    confidence: float         # 0.0 – 1.0
    reasoning: str
    slots: Slots = Field(default_factory=Slots)
    source: str = "keyword"   # "keyword" | "llm"

    # Valid intents
    VALID_INTENTS: ClassVar[set[str]] = {
        "SCHEDULE_CONFLICT",
        "PLAN_GENERATE",
        "COURSE_INFO",
        "CURRICULUM_RULE",
        "REGULATION_QA",
        "GENERAL_CHAT",
    }


# ──────────────────────────────────────────────────────────────
#  Tool Calls  (internal planner)
# ──────────────────────────────────────────────────────────────

class ToolCall(BaseModel):
    """Record of one tool execution inside the planner loop."""
    tool: str
    args: dict
    result: Any = None
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────
#  Outbound (to Module 07)
# ──────────────────────────────────────────────────────────────

class RouterResponse(BaseModel):
    """Assembled context that Module 07 (RAG/LLM Engine) receives."""
    session_id: str
    student_id: str
    original_query: str
    intent: str
    confidence: float
    reasoning: str
    slots: Slots
    tools_called: List[ToolCall]
    context: dict          # merged data from all tools
    conversation_history: List[Message]


# ──────────────────────────────────────────────────────────────
#  SSE Event types  (streamed back to Module 02 -> frontend)
# ──────────────────────────────────────────────────────────────

class SSEEvent(BaseModel):
    """One Server-Sent Event (type: clarify | refusal | context_ready | done | error | ...)."""
    type: str
    data: Any
