"""คลังความรู้ในหน่วยความจำ — โหลดจาก data/knowledge/*.md

ย่อมาจาก 07_rag_llm_engine/src/services/knowledge.py โดยตัด pydantic ออก
เพื่อให้ฟังก์ชันบน Vercel เบาที่สุด (ใช้แค่ stdlib)
"""
from __future__ import annotations

import json
from functools import lru_cache

from .retrieval import Document, HybridRetriever
from .store import DATA_DIR
from .text import chunk_text, expand_query, parse_frontmatter, section_hints, split_by_heading

CHUNK_CHARS = 900
CHUNK_OVERLAP = 150
TOP_K_BM25 = 20
TOP_K_VECTOR = 20
MIN_SCORE = 0.21


def _parse_list(raw: str) -> list[str]:
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


@lru_cache(maxsize=1)
def _index() -> tuple[HybridRetriever, list[str]]:
    docs: list[Document] = []
    folder = DATA_DIR / "knowledge"
    files: list[str] = []
    if folder.exists():
        for path in sorted(folder.glob("*.md")):
            files.append(path.name)
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            year = meta.get("effective_year", "")
            for heading, text in split_by_heading(body):
                for i, piece in enumerate(chunk_text(text, CHUNK_CHARS, CHUNK_OVERLAP)):
                    docs.append(Document(
                        doc_id=f"{path.stem}#{heading or 'intro'}#{i}",
                        title=meta.get("title", path.stem),
                        section=heading,
                        doc_type=meta.get("doc_type", "unknown"),
                        effective_year=int(year) if year.isdigit() else None,
                        program_ids=_parse_list(meta.get("program_ids", "")),
                        text=piece,
                    ))
    retriever = HybridRetriever()
    retriever.fit(docs)
    return retriever, files


def stats() -> dict:
    retriever, files = _index()
    return {"chunks": len(retriever.docs), "files": files}


def search(query: str, top_k: int = 6) -> list[dict]:
    retriever, _ = _index()
    hits = retriever.search(
        expand_query(query), top_k=top_k,
        top_k_bm25=TOP_K_BM25, top_k_vector=TOP_K_VECTOR,
        section_hints=section_hints(query),
    )
    return [{
        "doc_id": d.doc_id, "title": d.title, "section": d.section,
        "doc_type": d.doc_type, "score": round(score, 6), "text": d.text,
    } for d, score in hits]
