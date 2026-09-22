"""ตัวเลขที่ Prometheus มาเก็บ — ช่อง Monitoring & Analytics ในแผนภาพ"""
from __future__ import annotations

from prometheus_client import Counter


ROUTED = Counter(
    "rmutt_router_routed_total",
    "คำถามที่ Router ส่งต่อ แยกตาม intent, AI ที่เลือก และวิธีจัดประเภท",
    ["intent", "ai_target", "classifier"],
)
TOOL_CALLS = Counter(
    "rmutt_router_tool_calls_total", "เครื่องมือที่ Router เรียก", ["tool", "success"]
)

