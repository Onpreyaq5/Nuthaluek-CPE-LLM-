"""POST /api/chat — ถาม-ตอบเรื่องระเบียบและหลักสูตร พร้อมแหล่งอ้างอิง

body: {question, context:{plan, conflicts}}
ด่านกันมั่ว: ถามเรื่องที่คลังไม่มีข้อมูล หรือคะแนนค้นคืนต่ำกว่าเกณฑ์ -> ไม่ตอบ
"""
from _core.coverage import coverage_summary, find_gap
from _core.http import JsonHandler
from _core.knowledge import MIN_SCORE, search, stats
from _core.llm import api_key, generate

DISCLAIMER = ("ข้อมูลนี้เป็นคำแนะนำเบื้องต้นจากระบบ ไม่ใช่การยืนยันจากมหาวิทยาลัย "
              "โปรดตรวจสอบกับระบบทะเบียนและอาจารย์ที่ปรึกษาก่อนลงทะเบียนจริง")
NOT_FOUND = ("ไม่พบข้อมูลเรื่องนี้ในระเบียบและเอกสารหลักสูตรที่ระบบมีอยู่ "
             "แนะนำให้ติดต่อสำนักส่งเสริมวิชาการและงานทะเบียน (สวท.) หรืออาจารย์ที่ปรึกษาโดยตรง")
MAX_QUESTION = 500


class handler(JsonHandler):
    def get(self, query: dict) -> dict:
        """เช็คสถานะ + ประกาศขอบเขตข้อมูลที่ระบบมี"""
        return {"ok": True, "knowledge": stats(),
                "llm": "gemini" if api_key() else "rule_based",
                "coverage": coverage_summary()}

    def post(self, body: dict) -> dict:
        question = str(body.get("question") or "").strip()
        if not question:
            raise ValueError("ต้องส่ง question มาด้วย")
        # จำกัดความยาวก่อนเข้าโมดูลค้นคืน ไม่งั้นส่งข้อความยาวเป็นแสนตัวอักษร
        # แล้วขั้นตอนตัดคำ+BM25 จะกินเวลาจนฟังก์ชันหมดเวลาไปเอง
        if len(question) > MAX_QUESTION:
            raise ValueError(f"คำถามยาวเกินไป (ไม่เกิน {MAX_QUESTION} ตัวอักษร)")

        gap = find_gap(question)
        if gap is not None:
            return {"ok": True, "answer": gap.message, "sources": [],
                    "grounded": False, "provider": "coverage_gap", "disclaimer": DISCLAIMER}

        chunks = search(question, top_k=6)
        if not chunks or chunks[0]["score"] < MIN_SCORE:
            return {"ok": True, "answer": NOT_FOUND, "sources": [],
                    "grounded": False, "provider": "none", "disclaimer": DISCLAIMER}

        answer, provider, used = generate(question, chunks, body.get("context") or {})
        return {
            "ok": True,
            "answer": answer,
            "sources": [{k: c[k] for k in ("doc_id", "title", "section", "doc_type", "score")}
                        for c in used],
            "grounded": True,
            "provider": provider,
            "disclaimer": DISCLAIMER,
        }
