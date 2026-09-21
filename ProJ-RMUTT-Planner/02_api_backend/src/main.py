from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from src.adapters import get_log_sink
from src.api.v1 import api_router
from src.core.asyncio_compat import ensure_selector_event_loop_policy_on_windows
from src.core.config import get_settings
from src.core.db import get_engine
from src.core.envelope import error_envelope
from src.core.errors import AppError, Internal500Error, Validation422Error
from src.core.log_queue import get_log_queue
from src.core.logging import configure_logging, get_logger
from src.core.middleware import RequestContextMiddleware
from src.core.rate_limit import rate_limit
from src.core.redis import get_redis
from src.services.readiness_service import check_readiness

ensure_selector_event_loop_policy_on_windows()

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    get_log_queue().start(get_log_sink)
    yield
    await get_log_queue().stop_and_flush(get_log_sink)
    await get_engine().dispose()


app = FastAPI(title="RMUTT Study Planner API", version="0.1.0", lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


def _sanitize_validation_errors(errors: list[dict]) -> list[dict]:
    # exc.errors() ของ pydantic v2 อาจมี key "ctx" ที่เก็บ exception object ซึ่ง JSON serialize ไม่ได้
    return [{k: v for k, v in err.items() if k != "ctx"} for err in errors]


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    response = JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(exc.code, exc.message, exc.details),
    )
    retry_after = exc.details.get("retry_after") if exc.code == "RATE_429" else None
    if retry_after is not None:
        response.headers["Retry-After"] = str(retry_after)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    error = Validation422Error(
        "ข้อมูลที่ส่งมาไม่ถูกต้อง", details={"errors": _sanitize_validation_errors(exc.errors())}
    )
    return JSONResponse(
        status_code=error.status_code,
        content=error_envelope(error.code, error.message, error.details),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", error_type=type(exc).__name__)
    error = Internal500Error("เกิดข้อผิดพลาดที่ไม่คาดคิด")
    return JSONResponse(status_code=error.status_code, content=error_envelope(error.code, error.message))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> JSONResponse:
    checks = await check_readiness(get_settings(), get_engine(), get_redis())
    all_ready = all(checks.values())
    return JSONResponse(status_code=200 if all_ready else 503, content={"ready": all_ready, "checks": checks})


app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])
