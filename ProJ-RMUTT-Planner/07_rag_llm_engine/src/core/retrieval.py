"""การค้นคืนแบบผสม (Hybrid Retrieval) = BM25 (keyword) + TF-IDF cosine (semantic-ish)
รวมอันดับด้วย Reciprocal Rank Fusion

ทำไมไม่ใช้ Qdrant + sentence-transformers ตั้งแต่แรก:
คลังความรู้ของโปรเจกต์นี้เป็นเอกสารระเบียบ/หลักสูตรไม่กี่สิบหน้า การค้นแบบ in-memory
เร็วพอและไม่ต้องพึ่ง service ภายนอก ทำให้ CI และเครื่องของทุกคนรันได้เหมือนกัน
โครงสร้างแยก VectorIndex ออกมาแล้ว ถ้าจะเปลี่ยนไปใช้ Qdrant ให้ implement
interface เดิม (fit / search) แทนได้เลยโดยไม่ต้องแก้ส่วนอื่น
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field

from .text import tokenize


@dataclass
class Document:
    doc_id: str
    title: str
    section: str
    doc_type: str
    effective_year: int | None
    program_ids: list[str]
    text: str
    tokens: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.tokens:
            self.tokens = tokenize(f"{self.title} {self.section} {self.text}")


# ── BM25 ────────────────────────────────────────────────────────
class BM25Index:
    """BM25 Okapi — เขียนเองเพราะต้องการควบคุม tokenizer ภาษาไทย"""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs: list[Document] = []
        self.df: Counter[str] = Counter()
        self.tf: list[Counter[str]] = []
        self.doc_len: list[int] = []
        self.avg_len: float = 0.0

    def fit(self, docs: list[Document]) -> None:
        self.docs = docs
        self.tf = [Counter(d.tokens) for d in docs]
        self.doc_len = [len(d.tokens) for d in docs]
        self.avg_len = (sum(self.doc_len) / len(self.doc_len)) if self.doc_len else 0.0
        self.df = Counter()
        for counter in self.tf:
            self.df.update(counter.keys())

    def _idf(self, term: str) -> float:
        n = len(self.docs)
        df = self.df.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        q_tokens = tokenize(query)
        if not q_tokens or not self.docs:
            return []
        scores = [0.0] * len(self.docs)
        for term in set(q_tokens):
            idf = self._idf(term)
            if idf == 0.0:
                continue
            for i, counter in enumerate(self.tf):
                freq = counter.get(term, 0)
                if not freq:
                    continue
                denom = freq + self.k1 * (
                    1 - self.b + self.b * (self.doc_len[i] / (self.avg_len or 1))
                )
                scores[i] += idf * (freq * (self.k1 + 1)) / denom
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(i, s) for i, s in ranked if s > 0][:top_k]


# ── TF-IDF cosine ───────────────────────────────────────────────
class VectorIndex:
    """เวกเตอร์ TF-IDF + cosine similarity

    เปลี่ยนไปใช้ embedding จริง (bge-m3 / Qdrant) ได้โดยแทนที่คลาสนี้
    ให้มีเมธอด fit(docs) และ search(query, top_k) เหมือนเดิม
    """

    def __init__(self) -> None:
        self.docs: list[Document] = []
        self.vectors: list[dict[str, float]] = []
        self.idf: dict[str, float] = {}

    def fit(self, docs: list[Document]) -> None:
        self.docs = docs
        n = len(docs)
        df: Counter[str] = Counter()
        for d in docs:
            df.update(set(d.tokens))
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        self.vectors = [self._vectorize(d.tokens) for d in docs]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = len(tokens)
        vec = {t: (c / total) * self.idf.get(t, 1.0) for t, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {t: v / norm for t, v in vec.items()}

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        q_vec = self._vectorize(tokenize(query))
        if not q_vec or not self.vectors:
            return []
        scores: list[tuple[int, float]] = []
        for i, vec in enumerate(self.vectors):
            # วนบนเวกเตอร์ที่สั้นกว่าเพื่อความเร็ว
            small, large = (q_vec, vec) if len(q_vec) < len(vec) else (vec, q_vec)
            s = sum(w * large.get(t, 0.0) for t, w in small.items())
            if s > 0:
                scores.append((i, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# ── รวมอันดับ ───────────────────────────────────────────────────
def reciprocal_rank_fusion(
    rankings: list[list[tuple[int, float]]], k: int = 60
) -> list[tuple[int, float]]:
    """RRF: อันดับที่ดีในหลายวิธีย่อมชนะคะแนนดิบสูงในวิธีเดียว"""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, (idx, _score) in enumerate(ranking, start=1):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank)
    return sorted(fused.items(), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    def __init__(self, rrf_k: int = 60) -> None:
        self.bm25 = BM25Index()
        self.vector = VectorIndex()
        self.docs: list[Document] = []
        self.rrf_k = rrf_k

    def fit(self, docs: list[Document]) -> None:
        self.docs = docs
        self.bm25.fit(docs)
        self.vector.fit(docs)

    def search(
        self,
        query: str,
        top_k: int,
        top_k_bm25: int = 20,
        top_k_vector: int = 20,
        doc_type: str | None = None,
        effective_year: int | None = None,
        program_id: str | None = None,
    ) -> list[tuple[Document, float]]:
        """คืน [(document, relevance)] เรียงตามอันดับที่รวมด้วย RRF

        ค่า relevance ที่คืนออกไปคือ **cosine similarity (0–1)** ไม่ใช่คะแนน RRF
        เพราะ RRF ให้คะแนนตามลำดับ ผลอันดับ 1 จึงได้คะแนนเท่ากันเสมอไม่ว่าคำถาม
        จะเกี่ยวข้องจริงหรือไม่ ใช้เป็นเกณฑ์ตัด "ไม่พบข้อมูล" ไม่ได้
        """
        if not self.docs:
            return []
        bm25_hits = self.bm25.search(query, top_k_bm25)
        vector_hits = self.vector.search(query, top_k_vector)
        relevance = {idx: score for idx, score in vector_hits}

        fused = reciprocal_rank_fusion([bm25_hits, vector_hits], k=self.rrf_k)
        out: list[tuple[Document, float]] = []
        for idx, _rrf in fused:
            d = self.docs[idx]
            if doc_type and d.doc_type != doc_type:
                continue
            # กรองปีหลักสูตร: เอกสารที่ไม่ระบุปีถือว่าใช้ได้กับทุกรุ่น
            if effective_year and d.effective_year and d.effective_year > effective_year:
                continue
            if program_id and d.program_ids and "ALL" not in d.program_ids:
                if program_id not in d.program_ids:
                    continue
            out.append((d, relevance.get(idx, 0.0)))
            if len(out) >= top_k:
                break
        return out
