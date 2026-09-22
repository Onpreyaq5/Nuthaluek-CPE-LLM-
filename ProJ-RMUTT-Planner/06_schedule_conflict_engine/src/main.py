"""06_schedule_conflict_engine — Service Entrypoint
Deterministic collision detection & CP-SAT automated schedule planning engine
Internal microservice serving 02_api_backend and 03_ai_router_agent
"""
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router
from .config import get_settings

settings = get_settings()

app = FastAPI(
    title="06_schedule_conflict_engine",
    description="Deterministic Collision Detection & CP-SAT Auto Planner for RMUTT Planner",
    version="1.1.0",
)

# /metrics ให้ Prometheus (ช่อง Monitoring ในแผนภาพ)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# Secure CORS: Only enable if specific origins are explicitly configured in environment
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )


@app.get("/health")
def health():
    """Liveness probe required by Docker and CI"""
    return {
        "ok": True,
        "service": "06_schedule_conflict_engine",
        "status": "healthy",
        "demo_mode": settings.demo_mode,
        "version": "1.1.0",
    }


@app.get("/ready")
def readiness():
    """Readiness probe verifying operational settings"""
    return {
        "ready": True,
        "service": "06_schedule_conflict_engine",
        "demo_mode": settings.demo_mode,
        "course_data_url": settings.course_data_url,
        "data_integration_url": settings.data_integration_url,
    }


# Include engine routes
app.include_router(router)
