"""เก็บเวกเตอร์ TF-IDF ไว้ใน Qdrant แล้วให้ Qdrant เป็นคนค้น — ช่อง Vector DB ในแผนภาพ

ทำไมเป็น sparse vector ไม่ใช่ embedding แบบ dense:
เวกเตอร์ TF-IDF ของเราเป็น sparse อยู่แล้ว (มีค่าเฉพาะ n-gram ที่โผล่ในเอกสาร)
Qdrant เก็บ sparse vector ได้ตรง ๆ และคำนวณ dot product แบบ exact
เวกเตอร์ทุกตัวถูก normalize แล้ว dot product จึงเท่ากับ cosine ที่ VectorIndex คำนวณเอง
ผลคือคะแนนตรงกับโหมดในหน่วยความจำ ชุดคำถามมาตรฐานทั้ง 14 ข้อยังได้ผลเดิม
ถ้าเปลี่ยนไปใช้ embedding จริงภายหลัง แก้แค่ _vectorize กับ schema ของ collection

ถ้า Qdrant ล่มหรือยังไม่ขึ้น จะค้นในหน่วยความจำแทนทันที ผู้ใช้ไม่เห็นความต่าง
แล้วลองซิงก์ใหม่เป็นระยะ ๆ จนกว่า Qdrant จะกลับมา
"""
from __future__ import annotations

import logging
import threading
import time

import httpx

from .retrieval import Document, VectorIndex
from .text import tokenize

log = logging.getLogger(__name__)

VECTOR_NAME = "tfidf"
RETRY_SECONDS = 30.0
_BATCH = 64


class QdrantVectorIndex(VectorIndex):
    def __init__(self, url: str, collection: str, timeout: float = 5.0) -> None:
        super().__init__()
        self.url = url.rstrip("/")
        self.collection = collection
        self.timeout = timeout
        self.vocab: dict[str, int] = {}
        self.synced = False
        self._last_attempt = 0.0
        self._lock = threading.Lock()
        self.last_error: str | None = None

    # ── สถานะที่ /health รายงาน ─────────────────────────────────
    @property
    def backend(self) -> str:
        return "qdrant" if self.synced else "memory"

    # ── สร้าง index ───────────────────────────────────────────
    def fit(self, docs: list[Document]) -> None:
        super().fit(docs)
        # ให้หมายเลขกับทุก n-gram ที่มีในคลัง Qdrant ต้องการ index เป็นจำนวนเต็ม
        self.vocab = {}
        for vec in self.vectors:
            for term in vec:
                if term not in self.vocab:
                    self.vocab[term] = len(self.vocab)
        self.synced = False
        self._last_attempt = 0.0
        self._sync()

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.url, timeout=self.timeout)

    def _sparse(self, vec: dict[str, float]) -> dict:
        pairs = sorted((self.vocab[t], w) for t, w in vec.items() if t in self.vocab)
        return {"indices": [i for i, _ in pairs], "values": [w for _, w in pairs]}

    def _sync(self) -> None:
        """อัปโหลดเวกเตอร์ทั้งหมดขึ้น Qdrant — ล้มได้ ไม่ทำให้ service ล่ม"""
        with self._lock:
            self._last_attempt = time.monotonic()
            try:
                with self._client() as c:
                    c.delete(f"/collections/{self.collection}")
                    r = c.put(
                        f"/collections/{self.collection}",
                        json={"vectors": {}, "sparse_vectors": {VECTOR_NAME: {}}},
                    )
                    r.raise_for_status()
                    for start in range(0, len(self.vectors), _BATCH):
                        points = [
                            {
                                "id": i,
                                "vector": {VECTOR_NAME: self._sparse(vec)},
                                "payload": {
                                    "doc_id": self.docs[i].doc_id,
                                    "title": self.docs[i].title,
                                    "section": self.docs[i].section,
                                },
                            }
                            for i, vec in enumerate(
                                self.vectors[start:start + _BATCH], start=start
                            )
                            if vec
                        ]
                        if points:
                            r = c.put(
                                f"/collections/{self.collection}/points",
                                params={"wait": "true"},
                                json={"points": points},
                            )
                            r.raise_for_status()
                self.synced = True
                self.last_error = None
                log.info("ซิงก์เวกเตอร์ %s ชิ้นขึ้น Qdrant (%s) แล้ว", len(self.vectors), self.collection)
            except Exception as exc:  # noqa: BLE001 - Qdrant ล่มต้องไม่ทำให้ค้นไม่ได้
                self.synced = False
                self.last_error = str(exc)
                log.warning("ซิงก์ Qdrant ไม่สำเร็จ ใช้การค้นในหน่วยความจำแทน: %s", exc)

    # ── ค้น ────────────────────────────────────────────────────
    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        if not self.synced and self.vectors and time.monotonic() - self._last_attempt > RETRY_SECONDS:
            self._sync()
        if not self.synced:
            return super().search(query, top_k)

        # normalize ด้วย n-gram ทั้งหมดของคำถามก่อน แล้วค่อยตัดตัวที่ไม่มีในคลังทิ้ง
        # ถ้าตัดก่อน norm จะเล็กลง คะแนนจะสูงเกินจริงและไม่ตรงกับโหมดในหน่วยความจำ
        q_vec = self._vectorize(tokenize(query))
        sparse = self._sparse(q_vec)
        if not sparse["indices"]:
            return []
        try:
            with self._client() as c:
                r = c.post(
                    f"/collections/{self.collection}/points/query",
                    json={"query": sparse, "using": VECTOR_NAME, "limit": top_k},
                )
                r.raise_for_status()
                points = r.json()["result"]["points"]
            return [(int(p["id"]), float(p["score"])) for p in points if p["score"] > 0]
        except Exception as exc:  # noqa: BLE001
            log.warning("ค้นผ่าน Qdrant ไม่สำเร็จ ใช้หน่วยความจำแทน: %s", exc)
            self.synced = False
            self.last_error = str(exc)
            return super().search(query, top_k)
