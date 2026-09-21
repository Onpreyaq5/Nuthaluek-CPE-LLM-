"""รัน dev server บน Windows นอก Docker เท่านั้น

ปัญหา: `uvicorn src.main:app` (เรียกตรงจาก CLI) บน Windows ทำให้ asyncio.run() ของ uvicorn เอง
สร้าง ProactorEventLoop ไปแล้วก่อนจะ import src.main เสียอีก — ตั้ง event loop policy ในโค้ดแอปเอง
จึงไม่ทันเวลา (psycopg async ต่อ Postgres ไม่ได้ ได้ INTERFACE_ERROR ทุกครั้งที่มี query)
ไม่กระทบ Docker/Linux เลย (CMD ใน Dockerfile ยังคงเป็น `uvicorn src.main:app` ตรงตาม CLAUDE.md)

ใช้: python -m scripts.run_dev
"""

from __future__ import annotations

import uvicorn

from src.core.asyncio_compat import ensure_selector_event_loop_policy_on_windows

if __name__ == "__main__":
    ensure_selector_event_loop_policy_on_windows()
    # ไม่ใช้ reload=True: uvicorn สร้าง worker เป็น subprocess แยกที่ไม่รับ event loop policy
    # ที่ตั้งไว้ในโปรเซสหลักนี้ต่อ (ยังไม่ได้ทดสอบว่า reload ใช้ได้จริงบน Windows กับ psycopg async)
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
