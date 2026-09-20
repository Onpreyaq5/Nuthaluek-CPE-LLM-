from __future__ import annotations

from fastapi import APIRouter

from src.api.v1 import auth, chat, courses, feedback, plans, students

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(plans.router)
api_router.include_router(chat.router)
api_router.include_router(students.router)
api_router.include_router(feedback.router)
