from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters import get_student_data
from src.adapters.interfaces import StudentData
from src.api.deps import CurrentUser, current_user
from src.core.db import get_db
from src.core.envelope import success_envelope
from src.core.errors import Payload413Error
from src.schemas.envelope import SuccessEnvelope
from src.schemas.students import ImportResult, StudentProfile, TranscriptResponse
from src.services import auth_service, students_service

router = APIRouter(prefix="/students", tags=["students"])

_MAX_IMPORT_FILE_BYTES = 2 * 1024 * 1024  # 2 MB ตาม PLAN.md 4.4
_IMPORT_TOO_LARGE_MESSAGE = "ไฟล์ใหญ่เกินกำหนด (สูงสุด 2 MB)"


@router.get("/me/profile", response_model=SuccessEnvelope[StudentProfile])
async def get_profile(
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    student_data: StudentData = Depends(get_student_data),
) -> dict:
    await auth_service.get_current_student(db, user.student_id)  # ยืนยันว่าบัญชียังอยู่จริงใน DB
    data = await students_service.get_profile(student_data, user.student_id)
    return success_envelope(data.model_dump())


@router.get("/me/transcript", response_model=SuccessEnvelope[TranscriptResponse])
async def get_transcript(
    user: CurrentUser = Depends(current_user),
    student_data: StudentData = Depends(get_student_data),
) -> dict:
    data = await students_service.get_transcript(student_data, user.student_id)
    return success_envelope(data.model_dump(mode="json"))


@router.post("/me/import", response_model=SuccessEnvelope[ImportResult])
async def import_transcript(
    file: UploadFile,
    user: CurrentUser = Depends(current_user),
    student_data: StudentData = Depends(get_student_data),
) -> dict:
    # อ่านแค่ MAX+1 ไบต์พอให้รู้ว่าเกินหรือไม่ ไม่อ่านทั้งไฟล์ถ้าไม่จำเป็น (แม้ Starlette จะ buffer
    # multipart body ทั้งก้อนไว้ก่อนแล้วในระดับ framework — เรายังจำกัดฝั่งเราเองไม่ให้ถือ bytes เกินจำเป็น)
    raw = await file.read(_MAX_IMPORT_FILE_BYTES + 1)
    if len(raw) > _MAX_IMPORT_FILE_BYTES:
        raise Payload413Error(_IMPORT_TOO_LARGE_MESSAGE)

    data = await students_service.import_graduate_check(student_data, raw, student_id=user.student_id)
    return success_envelope(data.model_dump())
