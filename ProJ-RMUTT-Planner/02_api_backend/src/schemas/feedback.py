from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"target_type": "plan", "target_id": "12", "rating": 5, "reason": "แผนไม่ชนกันเลย"}
        }
    )

    target_type: Literal["plan", "chat_message", "explanation"]
    target_id: str
    rating: int = Field(ge=1, le=5)
    reason: str | None = None


class FeedbackResponse(BaseModel):
    feedback_id: int
