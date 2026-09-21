"""06_schedule_conflict_engine - Configuration & Environment Variables
"""
from functools import lru_cache
import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # Microservice URLs
    data_integration_url: str = Field(
        default=os.getenv("DATA_INTEGRATION_URL", "http://data_integration:8500")
    )
    course_data_url: str = Field(
        default=os.getenv("COURSE_DATA_URL", "http://course_data_services:8400")
    )

    # Solver parameters
    max_solver_seconds: int = Field(
        default=int(os.getenv("MAX_SOLVER_SECONDS", "10"))
    )
    max_plan_candidates: int = Field(
        default=int(os.getenv("MAX_PLAN_CANDIDATES", "5"))
    )

    # Academic credit constraints
    default_min_credits: int = Field(
        default=int(os.getenv("DEFAULT_MIN_CREDITS", "9"))
    )
    default_max_credits: int = Field(
        default=int(os.getenv("DEFAULT_MAX_CREDITS", "21"))
    )
    summer_max_credits: int = Field(
        default=int(os.getenv("SUMMER_MAX_CREDITS", "9"))
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
