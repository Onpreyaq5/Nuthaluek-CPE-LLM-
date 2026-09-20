from __future__ import annotations

import asyncio
import sys


def ensure_selector_event_loop_policy_on_windows() -> None:
    """psycopg (async) เชื่อมต่อผ่าน ProactorEventLoop (default ของ asyncio บน Windows) ไม่ได้
    ต้องสลับเป็น SelectorEventLoop ก่อนสร้าง event loop ใดๆ ที่จะคุยกับ Postgres —
    เรียกให้เร็วที่สุดตั้งแต่ตอน import ก่อน asyncio.run()/pytest-asyncio เริ่มสร้าง loop จริง
    (ไม่มีผลบน Linux/Docker เพราะใช้ selector loop เป็น default อยู่แล้ว)
    """
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
