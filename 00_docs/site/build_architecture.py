"""สร้างหน้าสถาปัตยกรรมสำหรับ GitHub Pages

    python 00_docs/site/build_architecture.py

อ่าน architecture.template.html (เป็นแค่เนื้อหน้า ไม่มี doctype/charset)
แล้วประกอบเป็นเอกสารเต็มไว้ที่ docs/architecture.html
ถ้าไม่มี charset ภาษาไทยจะกลายเป็นอักขระเพี้ยน และถ้าไม่มี viewport จอมือถือจะซูมออกจนอ่านไม่ออก
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SRC = HERE / "architecture.template.html"
OUT = REPO_ROOT / "docs" / "architecture.html"

DESCRIPTION = ("สถาปัตยกรรมระบบวางแผนและจัดตารางเรียน มทร.ธัญบุรี "
               "แยก 9 โมดูลทีละตัว พร้อม use case diagram มายด์แมป และขั้นตอนการทำงาน")


def main() -> None:
    src = SRC.read_text(encoding="utf-8")
    head, _, tail = src.partition("<style>")
    css, _, rest = tail.partition("</style>")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        '<!doctype html>\n<html lang="th">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f'<meta name="description" content="{DESCRIPTION}">\n'
        '<style>html,body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        + head + "<style>" + css + "</style>\n</head>\n<body>\n" + rest.lstrip()
        + "\n</body>\n</html>\n",
        encoding="utf-8",
    )
    print(f"เขียน {OUT.relative_to(REPO_ROOT)} ขนาด {OUT.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
