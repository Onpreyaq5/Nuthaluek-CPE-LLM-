"""สร้าง docs/architecture.pdf จาก docs/architecture.html

    python 00_docs/site/build_pdf.py

ใช้ Chrome หรือ Edge ที่มีอยู่แล้วในเครื่องสั่งพิมพ์เป็น PDF ไม่ต้องลงอะไรเพิ่ม
ต้องเสิร์ฟผ่าน http:// ไม่ใช่ file:// เพราะฟอนต์ไทยจาก Google Fonts
โหลดไม่ได้เมื่อเปิดจากไฟล์ตรง ๆ แล้วตัวอักษรจะตกไปใช้ฟอนต์สำรอง

สไตล์สำหรับพิมพ์อยู่ในบล็อก @media print ของ architecture.template.html
(กันไม่ให้ไดอะแกรมกับการ์ดขาดกลางหน้า และบังคับให้พิมพ์สีพื้นหลังออกมาด้วย)
"""
from __future__ import annotations

import http.server
import subprocess
import sys
import threading
from functools import partial
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
PAGE = "architecture.html"
OUT = DOCS / "architecture.pdf"
PORT = 8531

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


class Utf8Handler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler ไม่ประกาศ charset ทำให้ภาษาไทยเพี้ยนตอนเบราว์เซอร์อ่าน"""

    def guess_type(self, path):
        t = super().guess_type(path)
        return t + "; charset=utf-8" if str(t).startswith("text/") else t

    def log_message(self, *args):
        pass


def find_browser() -> str:
    for path in BROWSERS:
        if Path(path).exists():
            return path
    raise SystemExit("ไม่พบ Chrome หรือ Edge ในเครื่อง — ติดตั้งอย่างใดอย่างหนึ่งก่อน")


def main() -> None:
    if not (DOCS / PAGE).exists():
        raise SystemExit(f"ยังไม่มี {PAGE} — รัน build_architecture.py ก่อน")

    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", PORT), partial(Utf8Handler, directory=str(DOCS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        OUT.unlink(missing_ok=True)
        subprocess.run(
            [find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={OUT}", f"http://127.0.0.1:{PORT}/{PAGE}"],
            check=True, capture_output=True, timeout=180,
        )
    finally:
        server.shutdown()

    if not OUT.exists():
        raise SystemExit("เบราว์เซอร์ไม่ได้สร้างไฟล์ออกมา")
    print(f"เขียน {OUT.relative_to(REPO_ROOT)} ขนาด {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    sys.exit(main())
