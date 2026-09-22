"""07_rag_llm_engine — RAG ระเบียบ/หลักสูตร + สร้างคำตอบ

รัน: uvicorn src.main:app --host 0.0.0.0 --port 8700
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .api.routes import router
from .config import settings
from .core.metrics import VECTOR_BACKEND
from .services.knowledge import knowledge_base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    count = knowledge_base.load()
    VECTOR_BACKEND.set(1 if knowledge_base.vector_backend == "qdrant" else 0)
    log.info(
        "โหลดคลังความรู้แล้ว: %s chunk จาก %s ไฟล์ | LLM=%s | vector=%s | local=%s",
        count, len(knowledge_base.files),
        settings.llm_provider if settings.llm_enabled else "rule_based",
        knowledge_base.vector_backend,
        settings.local_model if settings.local_enabled else "off",
    )
    yield


app = FastAPI(
    title="07_rag_llm_engine",
    description="ค้นระเบียบ/หลักสูตร มทร.ธัญบุรี แล้วสร้างคำตอบพร้อมแหล่งอ้างอิง",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
# /metrics ให้ Prometheus (ช่อง Monitoring ในแผนภาพ) รวมตัวนับของ core/metrics.py ด้วย
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
