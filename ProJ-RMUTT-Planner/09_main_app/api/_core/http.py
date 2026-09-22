"""ตัวช่วยเขียน Vercel Python serverless function

Vercel มองไฟล์ api/*.py เป็นฟังก์ชันคนละตัว ไฟล์ที่ขึ้นต้นด้วย _ ไม่ถูก route
แต่ยัง bundle ไปด้วย จึงใช้เก็บโค้ดที่ใช้ร่วมกันได้
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ให้ import _core ได้ไม่ว่าจะถูกเรียกจากที่ไหน
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAX_BODY = 1_000_000   # 1 MB กันคนยิง payload ใหญ่ผิดปกติ
INTERNAL_MSG = "ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งในอีกสักครู่"


def allowed_origins() -> list[str]:
    """โดเมนที่เรียก API นี้ได้ ตั้งที่ ALLOWED_ORIGINS คั่นด้วยจุลภาค

    ทำไมต้องมี: เมื่อใส่ GEMINI_API_KEY แล้ว endpoint นี้กลายเป็น "ตัวกลางที่มีคีย์"
    ถ้าเปิด CORS ให้ทุกโดเมน ใครก็เอา URL ไปยิงเผาโควตาของเจ้าของคีย์ได้
    ไม่ตั้งค่า = เปิดให้ทุกโดเมน (สะดวกตอน dev แต่อย่าใช้ตอนมีคีย์จริง)
    """
    raw = (os.getenv("ALLOWED_ORIGINS") or "").strip()
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


def resolve_origin(request_origin: str | None) -> str:
    """เลือกค่า Access-Control-Allow-Origin ที่จะตอบกลับ

    ต้องสะท้อนโดเมนที่ขอมา ไม่ใช่ส่งรายการทั้งหมด เพราะสเปกให้ใส่ได้ค่าเดียว
    """
    allowed = allowed_origins()
    if not allowed:
        return "*"
    origin = (request_origin or "").strip().rstrip("/")
    return origin if origin in allowed else allowed[0]


class JsonHandler(BaseHTTPRequestHandler):
    """รับ-ส่ง JSON พร้อมจัดการ CORS และ error ให้เรียบร้อย

    คลาสลูกทำแค่ implement get(query) หรือ post(body)
    """

    def _send(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", resolve_origin(self.headers.get("Origin")))
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def _send_internal(self, exc: Exception) -> None:
        """ตอบ 500 แบบไม่หลุดรายละเอียดภายใน

        str(exc) มักมี path เต็มหรือโครงสร้างข้อมูลภายในติดมา ส่งให้ผู้ใช้ไม่ได้
        แต่ต้องยังเห็นใน log ของ Vercel ไม่งั้นดีบักไม่ได้เลย
        """
        traceback.print_exc(file=sys.stderr)
        self._send(500, {"ok": False, "error": {"code": "INTERNAL", "message": INTERNAL_MSG}})

    def do_OPTIONS(self) -> None:          # noqa: N802 - ชื่อตามที่ BaseHTTPRequestHandler กำหนด
        self._send(204, {})

    def do_GET(self) -> None:              # noqa: N802
        try:
            query = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            self._send(200, self.get(query))
        except NotImplementedError:
            self._send(405, {"ok": False, "error": {"code": "METHOD_NOT_ALLOWED",
                                                    "message": "endpoint นี้ไม่รองรับ GET"}})
        except FileNotFoundError as exc:
            self._send(404, {"ok": False, "error": {"code": "NOT_FOUND", "message": str(exc)}})
        except Exception as exc:           # noqa: BLE001 - ต้องไม่ให้ 500 หลุดไปแบบไม่มีข้อความ
            self._send_internal(exc)

    def do_POST(self) -> None:             # noqa: N802
        try:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                # header เพี้ยนต้องตอบ 400 ที่อ่านรู้เรื่อง ไม่ใช่ข้อความ int() ของ Python
                self._send(400, {"ok": False, "error": {"code": "BAD_REQUEST",
                                                        "message": "Content-Length ไม่ถูกต้อง"}})
                return
            if length < 0 or length > MAX_BODY:
                self._send(413, {"ok": False, "error": {"code": "TOO_LARGE",
                                                        "message": "ข้อมูลที่ส่งมาใหญ่เกินไป"}})
                return
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            if not isinstance(body, dict):
                raise ValueError("ต้องส่งข้อมูลเป็น JSON object")
            self._send(200, self.post(body))
        except NotImplementedError:
            self._send(405, {"ok": False, "error": {"code": "METHOD_NOT_ALLOWED",
                                                    "message": "endpoint นี้ไม่รองรับ POST"}})
        except json.JSONDecodeError:
            self._send(400, {"ok": False, "error": {"code": "BAD_JSON",
                                                    "message": "รูปแบบ JSON ไม่ถูกต้อง"}})
        except ValueError as exc:
            self._send(400, {"ok": False, "error": {"code": "VALIDATION", "message": str(exc)}})
        except FileNotFoundError as exc:
            self._send(404, {"ok": False, "error": {"code": "NOT_FOUND", "message": str(exc)}})
        except Exception as exc:           # noqa: BLE001
            self._send_internal(exc)

    # ── คลาสลูก override ──────────────────────────────────────
    def get(self, query: dict) -> dict:
        raise NotImplementedError

    def post(self, body: dict) -> dict:
        raise NotImplementedError

    def log_message(self, *args) -> None:  # ปิด log ของ stdlib ไม่ให้รก
        pass
