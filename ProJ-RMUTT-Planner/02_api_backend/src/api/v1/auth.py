from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import SESSION_COOKIE_NAME, CurrentUser, current_user
from src.core.config import get_settings
from src.core.db import get_db
from src.core.envelope import success_envelope
from src.schemas.auth import LoginRequest, LoginResponse, MeResponse
from src.schemas.envelope import SuccessEnvelope
from src.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SuccessEnvelope[LoginResponse])
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    settings = get_settings()
    student, token = await auth_service.login(
        db, username=payload.username, password=payload.password, settings=settings
    )
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        secure=settings.CORS_ORIGINS.startswith("https://"),
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
    )
    data = LoginResponse(username=student.username, student_id=student.student_id, role=student.role)
    return success_envelope(data.model_dump())


@router.get("/me", response_model=SuccessEnvelope[MeResponse])
async def me(user: CurrentUser = Depends(current_user), db: AsyncSession = Depends(get_db)) -> dict:
    student = await auth_service.get_current_student(db, user.student_id)
    data = MeResponse(username=student.username, student_id=student.student_id, role=student.role)
    return success_envelope(data.model_dump())


@router.post("/logout", response_model=SuccessEnvelope[dict])
async def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return success_envelope({})
