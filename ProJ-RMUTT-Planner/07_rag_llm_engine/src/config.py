"""ค่าตั้งของโมดูล 07 — อ่านจาก environment ทั้งหมด ไม่ hardcode secret"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass
class Settings:
    # ── แหล่งเอกสาร ──────────────────────────────────────────────
    knowledge_dir: Path = field(
        default_factory=lambda: Path(os.getenv("KNOWLEDGE_DIR", BASE_DIR / "data" / "knowledge"))
    )
    seed_dir: Path = field(
        default_factory=lambda: Path(os.getenv("SEED_DIR", BASE_DIR / "data" / "seed"))
    )

    # ── การแบ่ง chunk ───────────────────────────────────────────
    chunk_chars: int = _int("CHUNK_CHARS", 900)
    chunk_overlap: int = _int("CHUNK_OVERLAP", 150)

    # ── การค้นคืน ───────────────────────────────────────────────
    top_k_bm25: int = _int("TOP_K_BM25", 20)
    top_k_vector: int = _int("TOP_K_VECTOR", 20)
    top_k_final: int = _int("TOP_K_FINAL", 6)
    rrf_k: int = _int("RRF_K", 60)
    # ถ้าคะแนนสูงสุดต่ำกว่านี้ ถือว่า "ไม่พบข้อมูล" และห้ามให้ LLM เดา
    min_score: float = _float("MIN_SCORE", 0.21)

    # ── LLM ─────────────────────────────────────────────────────
    llm_provider: str = os.getenv("LLM_PROVIDER", "rule_based")  # rule_based|gemini|openai|anthropic
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_timeout: int = _int("LLM_TIMEOUT", 30)

    # ── บริการอื่นในระบบ ────────────────────────────────────────
    data_integration_url: str = os.getenv("DATA_INTEGRATION_URL", "http://data_integration:8500")
    schedule_engine_url: str = os.getenv("SCHEDULE_ENGINE_URL", "http://schedule_engine:8600")

    # ── กติกาหน่วยกิต (ใช้ตรวจคำตอบไม่ให้ขัดระเบียบ) ─────────────
    min_credits: int = _int("DEFAULT_MIN_CREDITS", 9)
    max_credits: int = _int("DEFAULT_MAX_CREDITS", 21)
    summer_max_credits: int = _int("SUMMER_MAX_CREDITS", 9)

    @property
    def llm_enabled(self) -> bool:
        """เรียก LLM จริงได้ก็ต่อเมื่อเลือก provider และมี API key"""
        return self.llm_provider != "rule_based" and bool(self.llm_api_key)


settings = Settings()

DISCLAIMER = (
    "ข้อมูลนี้เป็นคำแนะนำเบื้องต้นจากระบบ ไม่ใช่การยืนยันจากมหาวิทยาลัย "
    "โปรดตรวจสอบกับระบบทะเบียนและอาจารย์ที่ปรึกษาก่อนลงทะเบียนจริง"
)

NOT_FOUND_MESSAGE = (
    "ไม่พบข้อมูลเรื่องนี้ในระเบียบและเอกสารหลักสูตรที่ระบบมีอยู่ "
    "แนะนำให้ติดต่อสำนักส่งเสริมวิชาการและงานทะเบียน (สวท.) หรืออาจารย์ที่ปรึกษาโดยตรง"
)
