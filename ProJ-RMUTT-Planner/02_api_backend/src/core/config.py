from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# core/config.py -> core -> src -> 02_api_backend -> parent (root ของ monorepo ที่วางโมดูล 03-08 ไว้ข้างๆ)
_MODULES_ROOT_DEFAULT = str(Path(__file__).resolve().parents[3])


class TimeoutPolicy(BaseModel):
    seconds: float
    retries: int


class TimeoutSettings(BaseModel):
    read: TimeoutPolicy
    validate_plan: TimeoutPolicy
    auto_plan: TimeoutPolicy
    write: TimeoutPolicy
    chat_start: TimeoutPolicy
    chat_idle: TimeoutPolicy
    chat_total: TimeoutPolicy


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # infra
    DATABASE_URL: str = "postgresql+psycopg://rmutt:change_me_please@localhost:5432/rmutt"
    REDIS_URL: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "INFO"

    # auth / บัญชีเดโม (PLAN.md หัวข้อ 5)
    DEMO_USERNAME: str = "admin"
    DEMO_PASSWORD: str = "admin1234"
    DEMO_STUDENT_ID: str = "6500000000"
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "http://localhost:5173"

    # adapter (PLAN.md หัวข้อ 3.2) — mock | inprocess | http
    ADAPTER_04: str = "mock"
    ADAPTER_05: str = "mock"
    ADAPTER_06: str = "mock"
    ADAPTER_07: str = "mock"
    ADAPTER_08: str = "mock"
    ROUTER_URL: str = "http://router:8001"

    # URL ของโมดูล 04-08 เมื่อ ADAPTER_xx=http — PLACEHOLDER: ยังไม่มีสัญญาจริงจากทีม (ดูสรุปท้าย Prompt 3)
    COURSE_CATALOG_URL: str = "http://course_catalog:8400"
    STUDENT_DATA_URL: str = "http://student_data:8500"
    PLAN_ENGINE_URL: str = "http://plan_engine:8600"
    EXPLAINER_URL: str = "http://explainer:8700"
    LOG_SINK_URL: str = "http://log_sink:8800"

    # inprocess loader (ADAPTER_04/05=inprocess): ชื่อโฟลเดอร์โมดูลที่วางไว้ข้างๆ 02_api_backend ใต้ MODULES_ROOT
    # MODULE_04_DIR เป็น PLACEHOLDER เพราะยังไม่ทราบชื่อโฟลเดอร์จริงของโมดูล 04 (ยังไม่มีใน GitHub)
    MODULES_ROOT: str = _MODULES_ROOT_DEFAULT
    MODULE_04_DIR: str = "04_course_data"
    MODULE_05_DIR: str = "05_data_integration"

    # timeout / retry ต่อประเภทคำขอ (PLAN.md ตาราง 3.3) หน่วยวินาที
    TIMEOUT_READ_SECONDS: float = 5.0
    RETRY_READ: int = 1
    TIMEOUT_VALIDATE_SECONDS: float = 5.0
    RETRY_VALIDATE: int = 1
    TIMEOUT_AUTO_SECONDS: float = 15.0
    RETRY_AUTO: int = 0
    TIMEOUT_WRITE_SECONDS: float = 10.0
    RETRY_WRITE: int = 0
    TIMEOUT_CHAT_START_SECONDS: float = 15.0
    TIMEOUT_CHAT_IDLE_SECONDS: float = 30.0
    TIMEOUT_CHAT_TOTAL_SECONDS: float = 120.0

    # แชต (PLAN.md หัวข้อ 6) — ทั้งสองตัวเป็น PLACEHOLDER:
    # TOOL_ALLOWLIST ควรมาจาก INTENT -> TOOL MAP ใน 03_ai_router_agent/03_process.txt ซึ่งยังไม่มีในสภาพแวดล้อมนี้
    # CURRENT_TERM ไม่มีที่มาชัดเจนจาก ChatRequest (ไม่มี field term) ต้องยืนยันกับทีมว่าจะเอามาจากไหนจริง
    TOOL_ALLOWLIST: str = "search_knowledge,search_courses,check_schedule_conflict,generate_plan"
    CURRENT_TERM: str = "1/2569"

    @property
    def tool_allowlist_set(self) -> set[str]:
        return {name.strip() for name in self.TOOL_ALLOWLIST.split(",") if name.strip()}

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _cors_not_wildcard(cls, v: str) -> str:
        if v.strip() == "*":
            raise ValueError('CORS_ORIGINS ห้ามเป็น "*" เมื่อ allow_credentials=True')
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def timeouts(self) -> TimeoutSettings:
        return TimeoutSettings(
            read=TimeoutPolicy(seconds=self.TIMEOUT_READ_SECONDS, retries=self.RETRY_READ),
            validate_plan=TimeoutPolicy(seconds=self.TIMEOUT_VALIDATE_SECONDS, retries=self.RETRY_VALIDATE),
            auto_plan=TimeoutPolicy(seconds=self.TIMEOUT_AUTO_SECONDS, retries=self.RETRY_AUTO),
            write=TimeoutPolicy(seconds=self.TIMEOUT_WRITE_SECONDS, retries=self.RETRY_WRITE),
            chat_start=TimeoutPolicy(seconds=self.TIMEOUT_CHAT_START_SECONDS, retries=0),
            chat_idle=TimeoutPolicy(seconds=self.TIMEOUT_CHAT_IDLE_SECONDS, retries=0),
            chat_total=TimeoutPolicy(seconds=self.TIMEOUT_CHAT_TOTAL_SECONDS, retries=0),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
