"""สร้างสไลด์บทที่ 7 เป็นหน้าเว็บและ PDF ขนาด 16:9

    python 00_docs/site/build_ch07.py

เขียน docs/ch07.html แล้วสั่ง Chrome/Edge พิมพ์เป็น docs/ch07-slides.pdf
หนึ่ง section.slide = หนึ่งหน้า ขนาด 1280x720 พอดีกับสไลด์จอกว้าง
เอาไปวางใน PowerPoint หรือ Google Slides เป็นภาพพื้นหลังได้เลย

ต้องเสิร์ฟผ่าน http:// ไม่ใช่ file:// เพราะฟอนต์ไทยจาก Google Fonts
โหลดไม่ได้เมื่อเปิดจากไฟล์ตรง ๆ แล้วตัวอักษรจะตกไปใช้ฟอนต์สำรอง
"""
from __future__ import annotations

import http.server
import subprocess
import sys
import threading
from functools import partial
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DOCS = REPO_ROOT / "docs"
SRC = HERE / "ch07.template.html"
PAGE = DOCS / "ch07.html"
PDF = DOCS / "ch07-slides.pdf"
PORT = 8532

DESCRIPTION = ("สไลด์บทที่ 7 RAG + LLM Engine ของระบบวางแผนการเรียน มทร.ธัญบุรี "
               "— สถาปัตยกรรม มายด์แมป use case และวิธีทำงานแบบเข้าใจง่าย")

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


def build_page() -> None:
    src = SRC.read_text(encoding="utf-8")
    head, _, tail = src.partition("<style>")
    css, _, rest = tail.partition("</style>")
    DOCS.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(
        '<!doctype html>\n<html lang="th">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f'<meta name="description" content="{DESCRIPTION}">\n'
        '<style>html,body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        + head + "<style>" + css + "</style>\n</head>\n<body>\n" + rest.lstrip()
        + "\n</body>\n</html>\n",
        encoding="utf-8",
    )
    print(f"เขียน {PAGE.relative_to(REPO_ROOT)} ขนาด {PAGE.stat().st_size / 1024:.0f} KB")


def build_pdf() -> None:
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", PORT), partial(Utf8Handler, directory=str(DOCS)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        PDF.unlink(missing_ok=True)
        subprocess.run(
            [find_browser(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={PDF}", f"http://127.0.0.1:{PORT}/{PAGE.name}"],
            check=True, capture_output=True, timeout=180,
        )
    finally:
        server.shutdown()
    if not PDF.exists():
        raise SystemExit("เบราว์เซอร์ไม่ได้สร้างไฟล์ออกมา")
    print(f"เขียน {PDF.relative_to(REPO_ROOT)} ขนาด {PDF.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    build_page()
    build_pdf()
    sys.exit(0)
