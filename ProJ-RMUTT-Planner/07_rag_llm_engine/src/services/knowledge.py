"""โหลดเอกสารความรู้ (ระเบียบ/หลักสูตร/ปฏิทิน/FAQ) เข้า index แล้วให้ค้นหา"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..config import settings
from ..core.retrieval import Document, HybridRetriever
from ..core.text import (
    chunk_text,
    expand_query,
    parse_frontmatter,
    section_hints,
    split_by_heading,
)
from ..models.schemas import Chunk

log = logging.getLogger(__name__)


def _parse_list(raw: str) -> list[str]:
    """'["CPE-2566", "ALL"]' -> ["CPE-2566", "ALL"]"""
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(x) for x in value]
    except json.JSONDecodeError:
        pass
    return [x.strip().strip('"').strip("'") for x in raw.strip("[]").split(",") if x.strip()]


def load_documents(knowledge_dir: Path) -> list[Document]:
    """อ่านไฟล์ .md ทุกไฟล์ในโฟลเดอร์ แล้วแตกเป็น chunk ตามหัวข้อ"""
    docs: list[Document] = []
    if not knowledge_dir.exists():
        log.warning("ไม่พบโฟลเดอร์เอกสาร: %s", knowledge_dir)
        return docs

    for path in sorted(knowledge_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)
        title = meta.get("title", path.stem)
        doc_type = meta.get("doc_type", "unknown")
        year_raw = meta.get("effective_year", "")
        effective_year = int(year_raw) if year_raw.isdigit() else None
        program_ids = _parse_list(meta.get("program_ids", ""))

        for heading, section_text in split_by_heading(body):
            for i, piece in enumerate(
                chunk_text(section_text, settings.chunk_chars, settings.chunk_overlap)
            ):
                docs.append(
                    Document(
                        doc_id=f"{path.stem}#{heading or 'intro'}#{i}",
                        title=title,
                        section=heading,
                        doc_type=doc_type,
                        effective_year=effective_year,
                        program_ids=program_ids,
                        text=piece,
                    )
                )
    log.info("โหลดเอกสาร %s ไฟล์ -> %s chunk", len(list(knowledge_dir.glob('*.md'))), len(docs))
    return docs


def _vector_index():
    """ตั้ง QDRANT_URL = ใช้ Qdrant เป็น Vector DB, ไม่ตั้ง = ค้นในหน่วยความจำ"""
    if settings.qdrant_url:
        from ..core.qdrant_index import QdrantVectorIndex

        return QdrantVectorIndex(settings.qdrant_url, settings.qdrant_collection)
    return None


class KnowledgeBase:
    """คลังความรู้ — BM25 อยู่ในหน่วยความจำ ขาเวกเตอร์อยู่ใน Qdrant ถ้าตั้งค่าไว้"""

    def __init__(self) -> None:
        self.retriever = HybridRetriever(rrf_k=settings.rrf_k, vector=_vector_index())
        self.documents: list[Document] = []
        self.files: list[str] = []

    def load(self, knowledge_dir: Path | None = None) -> int:
        directory = knowledge_dir or settings.knowledge_dir
        self.documents = load_documents(directory)
        self.files = [p.name for p in sorted(directory.glob("*.md"))] if directory.exists() else []
        self.retriever.fit(self.documents)
        return len(self.documents)

    @property
    def ready(self) -> bool:
        return bool(self.documents)

    @property
    def vector_backend(self) -> str:
        """qdrant | memory — บอกว่าตอนนี้ขาเวกเตอร์ค้นจากที่ไหนจริง"""
        return getattr(self.retriever.vector, "backend", "memory")

    def search(
        self,
        query: str,
        top_k: int | None = None,
        doc_type: str | None = None,
        effective_year: int | None = None,
        program_id: str | None = None,
    ) -> list[Chunk]:
        # ขยายคำถามที่จุดเดียว เพื่อให้ /knowledge/search กับ /generate
        # ได้ผลเหมือนกันเสมอสำหรับคำถามเดียวกัน
        # (เดิมขยายเฉพาะใน /generate ทำให้สองปลายทางให้อันดับต่างกัน)
        hits = self.retriever.search(
            expand_query(query),
            top_k=top_k or settings.top_k_final,
            top_k_bm25=settings.top_k_bm25,
            top_k_vector=settings.top_k_vector,
            doc_type=doc_type,
            effective_year=effective_year,
            program_id=program_id,
            section_hints=section_hints(query),
        )
        return [
            Chunk(
                doc_id=d.doc_id,
                title=d.title,
                section=d.section,
                doc_type=d.doc_type,
                effective_year=d.effective_year,
                score=round(score, 6),
                text=d.text,
            )
            for d, score in hits
        ]


knowledge_base = KnowledgeBase()
