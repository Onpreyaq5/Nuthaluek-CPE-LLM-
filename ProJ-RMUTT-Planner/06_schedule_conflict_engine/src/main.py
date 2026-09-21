"""06_schedule_conflict_engine — Service Entrypoint
Core collision detection & CP-SAT automated schedule planning engine
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router

app = FastAPI(
    title="06_schedule_conflict_engine",
    description="Deterministic Collision Detection & CP-SAT Auto Planner for RMUTT Planner",
    version="1.0.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check endpoint required by Docker and CI"""
    return {
        "ok": True,
        "service": "06_schedule_conflict_engine",
        "status": "healthy",
        "version": "1.0.0",
    }


# Include engine routes
app.include_router(router)
