from __future__ import annotations

from collections.abc import AsyncIterator

from src.adapters.interfaces import AnswerGenerator

_GENERIC_ERROR_MESSAGE = "ระบบ AI ขัดข้อง"


async def run_chat_turn(
    router_events: AsyncIterator[dict],
    answer_generator: AnswerGenerator,
    *,
    question: str,
    history: list[dict],
) -> AsyncIterator[dict]:
    """รับ event ภายในจาก ChatRouter.stream() (key "kind") แล้วผลิต public event (key "type") ให้
    src/api/v1/chat.py ส่งต่อ (ผ่าน sanitize_event) — ตัดสินใจว่าจะเรียกตัวสร้างคำตอบของ 07 หรือไม่

    "done" ที่ผลิตออกมาไม่มี message_id (ผู้เรียกต้องเติม assistant_message.id จริงก่อนส่งต่อ sanitize_event
    เสมอ — orchestrator ชั้นนี้ไม่รู้จัก DB row ของ 02 เลย)

    กติกา: เรียก answer_generator.generate() ได้สูงสุดครั้งเดียวต่อรอบ, ไม่ส่ง context_ready/router event
    ภายในออกไปตรงๆ, ไม่ประกาศ done (สำเร็จ) ถ้าไม่ได้เรียก generator จริงเมื่อจำเป็น (context_ready),
    outcome กำกวม -> error แทนการแกล้งสำเร็จ"""
    context_data: dict | None = None

    async for event in router_events:
        kind = event.get("kind")

        if kind == "tool_start":
            yield {"type": "tool_start", "tool": event["tool"]}
            continue

        if kind == "tool_end":
            yield {"type": "tool_end", "tool": event["tool"]}
            continue

        if kind == "sources":
            yield {"type": "sources", "items": event["items"]}
            continue

        if kind == "clarify":
            yield {"type": "token", "text": event.get("question", "")}
            continue

        if kind == "context_ready":
            context_data = event.get("context") or {}
            continue

        if kind == "refusal":
            yield {"type": "token", "text": event.get("message", "")}
            yield {"type": "done"}
            return

        if kind == "error":
            yield {"type": "error", "code": "UPSTREAM_502", "message": _GENERIC_ERROR_MESSAGE}
            return

        if kind == "router_done":
            outcome = event.get("outcome")

            if outcome == "clarify":
                yield {"type": "done"}
                return

            if outcome == "context_ready":
                if context_data is None:
                    # ไม่ควรเกิดถ้า 03 ทำตามสัญญา (ต้องมี context_ready มาก่อน router_done ที่มี
                    # outcome=context_ready เสมอ) — ถือว่าลำดับ event ผิดปกติ ห้ามแกล้งตอบสำเร็จ
                    yield {"type": "error", "code": "UPSTREAM_502", "message": _GENERIC_ERROR_MESSAGE}
                    return
                async for gen_event in answer_generator.generate(
                    question=question, context=context_data, history=history
                ):
                    gen_type = gen_event.get("type")
                    if gen_type == "token":
                        yield {"type": "token", "text": gen_event.get("text", "")}
                    elif gen_type == "sources":
                        yield {"type": "sources", "items": gen_event.get("items", [])}
                yield {"type": "done"}
                return

            # outcome เป็น None หรือค่าที่ไม่รู้จัก -> กำกวม (เช่น 03 จบสตรีมโดยไม่เคยส่ง clarify/
            # context_ready มาก่อนเลย) ห้ามสร้างคำตอบว่างหรือแกล้งว่าสำเร็จ
            yield {"type": "error", "code": "UPSTREAM_502", "message": _GENERIC_ERROR_MESSAGE}
            return

        # kind ที่ไม่รู้จัก -> ข้าม (กันโค้ด adapter เวอร์ชันใหม่ส่ง kind แปลกมาโดยไม่ได้ตั้งใจ)

    # router_events หมดโดยไม่มี event ปิดท้ายเลย (router_done/refusal/error) — ผิดปกติ ปล่อยให้
    # StopAsyncIteration ของ generator นี้เองสะท้อนไปถึงผู้เรียก (chat.py จัดการเป็น UPSTREAM_502 มิดสตรีมอยู่แล้ว)
