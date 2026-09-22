"""ตัวเลขที่ Prometheus มาเก็บ — ช่อง Monitoring & Analytics ในแผนภาพ

GET /metrics  ->  Prometheus scrape ทุก 15 วินาที แล้ว Grafana เอาไปวาดกราฟ
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


ANSWERS = Counter(
    "rmutt_rag_answers_total",
    "คำตอบที่สร้าง แยกตาม AI ที่ใช้ และมีเอกสารรองรับหรือไม่",
    ["ai_target", "provider", "grounded"],
)
RETRIEVAL_TOP_SCORE = Histogram(
    "rmutt_rag_top_score", "คะแนนค้นคืนสูงสุดของแต่ละคำถาม",
    buckets=(0.05, 0.1, 0.15, 0.21, 0.3, 0.4, 0.5, 0.7, 1.0),
)
VECTOR_BACKEND = Gauge(
    "rmutt_rag_vector_backend_qdrant", "1 = ขาเวกเตอร์ค้นจาก Qdrant, 0 = ค้นในหน่วยความจำ"
)

