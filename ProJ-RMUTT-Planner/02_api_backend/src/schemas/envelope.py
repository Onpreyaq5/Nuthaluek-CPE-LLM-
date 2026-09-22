from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Meta(BaseModel):
    request_id: str
    took_ms: float


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = Field(default_factory=dict)


class SuccessEnvelope(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    ok: Literal[True]
    data: T
    meta: Meta


class ErrorEnvelope(BaseModel):
    ok: Literal[False]
    error: ErrorDetail
    meta: Meta
