"""เซิร์ฟเวอร์จำลอง Vercel Python functions สำหรับพัฒนาในเครื่อง

บน Vercel ไฟล์ api/*.py จะกลายเป็น serverless function อัตโนมัติ
แต่ตอนรันในเครื่อง ต้องมีตัวกลางคอยเรียก handler ให้ สคริปต์นี้ทำหน้าที่นั้น

รัน:
    python scripts/dev_server.py            # ฟังที่ 127.0.0.1:8009
    PY_DEV_URL=http://127.0.0.1:8009 npm run dev

แล้ว Next.js จะ rewrite /api/* มาที่นี่ (ดู next.config.mjs)
"""
from __future__ import annotations

import importlib.util
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "api"
sys.path.insert(0, str(API_DIR))

PORT = int(os.getenv("PORT", "8009"))
# ใน container ต้องผูก 0.0.0.0 ไม่งั้น container อื่นต่อเข้ามาไม่ได้
# ตอนรันในเครื่องปล่อยเป็น 127.0.0.1 ไว้ จะได้ไม่เปิดพอร์ตออกนอกเครื่องโดยไม่ตั้งใจ
HOST = os.getenv("HOST", "127.0.0.1")


def load_handler(name: str):
    """โหลดคลาส handler จากไฟล์ api/<name>.py"""
    path = API_DIR / f"{name}.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"api_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "handler", None)


class Router(BaseHTTPRequestHandler):
    """ส่งต่อ /api/<ชื่อ> ไปยัง handler ของไฟล์นั้น"""

    def _dispatch(self, method: str) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            self.send_error(404, "ใช้ได้เฉพาะ /api/*")
            return

        name = path[len("/api/"):].strip("/").split("/")[0]
        cls = load_handler(name)
        if cls is None:
            self.send_error(404, f"ไม่มีฟังก์ชัน api/{name}.py")
            return

        # ยืม handler ของ Vercel มาใช้กับ connection เดิม
        inst = cls.__new__(cls)
        inst.rfile = self.rfile
        inst.wfile = self.wfile
        inst.headers = self.headers
        inst.path = self.path
        inst.request_version = self.request_version
        inst.requestline = self.requestline
        inst.client_address = self.client_address
        inst.server = self.server
        inst.command = method
        inst.close_connection = True
        getattr(inst, f"do_{method}")()

    def do_GET(self):      # noqa: N802
        self._dispatch("GET")

    def do_POST(self):     # noqa: N802
        self._dispatch("POST")

    def do_OPTIONS(self):  # noqa: N802
        self._dispatch("OPTIONS")

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")


if __name__ == "__main__":
    print(f"Python API server: http://{HOST}:{PORT}/api/*")
    print("  endpoint ที่มี:", ", ".join(sorted(p.stem for p in API_DIR.glob("*.py") if not p.stem.startswith("_"))))
    HTTPServer((HOST, PORT), Router).serve_forever()
