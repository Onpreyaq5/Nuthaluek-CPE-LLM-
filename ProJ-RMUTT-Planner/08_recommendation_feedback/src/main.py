"""Recommendation, feedback, analytics and notification service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.router import router
from src.core.config import get_settings
from src.core.database import init_db
from src.core.http import RequestContextMiddleware, register_exception_handlers


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


settings = get_settings()
app = FastAPI(
    title="RMUTT Recommendation & Feedback",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Request-ID", "X-Internal-Token"],
)
register_exception_handlers(app)
app.include_router(router)
