from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"username": "admin", "password": "admin1234"}}
    )

    username: str
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"username": "admin", "student_id": "6500000000", "role": "student"}
        }
    )

    username: str
    student_id: str
    role: str


class MeResponse(LoginResponse):
    pass
