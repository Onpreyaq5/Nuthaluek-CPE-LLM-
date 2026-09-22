"""สร้างหน้าเดโมไฟล์เดียวสำหรับ GitHub Pages

ทำไมต้องมี: ตัวเต็มใน 09_main_app ต้องมีฟังก์ชัน Python ฝั่งเซิร์ฟเวอร์ จึงต้อง deploy ที่ Vercel
หน้านี้ยกตรรกะตรวจตารางชนกับตัวจัดตารางไปไว้ในเบราว์เซอร์ทั้งหมด เลยวางบน GitHub Pages ได้เลย
โดยไม่ต้องมีเซิร์ฟเวอร์และไม่มีค่าใช้จ่าย

ต่างจากตัวเต็ม: ไม่มีหน้าแชตถามระเบียบ (ต้องใช้ RAG ฝั่งเซิร์ฟเวอร์)
และเปลี่ยนการส่งออก .ics เป็นการคัดลอกข้อความ

    python ProJ-RMUTT-Planner/09_main_app/static_demo/build.py

ตรรกะในหน้านี้เป็นการพอร์ตจาก api/_core/conflicts.py และ api/_core/planner.py
ถ้าแก้ตรรกะฝั่ง Python แล้ว อย่าลืมแก้ใน template.html ให้ตรงกันด้วย
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parent                      # .../09_main_app
REPO_ROOT = APP.parents[1]             # .../<repo>
OUT = REPO_ROOT / "docs" / "index.html"

# เอาเฉพาะฟิลด์ที่หน้าเว็บใช้ จะได้ไม่พาข้อมูลส่วนเกินขึ้นไปด้วย
# ไม่เอา slots_mask ไปด้วย เพราะเป็นเลข 182 บิต ที่ JSON.parse ของ JS เก็บได้แม่นแค่ 53 บิต
# ฝั่งเบราว์เซอร์คำนวณ mask เองจาก meetings ด้วย BigInt
KEEP = ("id", "course_code", "section", "course_name", "credits", "category",
        "suggested_year", "meetings", "exams", "seat_total",
        "seat_taken", "prerequisites", "teachers", "is_online", "priority_score")


def load(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "term": raw["term"],
        "term_start": raw.get("term_start"),
        "weeks": raw.get("weeks", 16),
        "credit_rule": raw.get("credit_rule", {}),
        "disclaimer": raw.get("disclaimer", ""),
        "sections": [{k: s[k] for k in KEEP if k in s} for s in raw["sections"]],
    }


def main() -> None:
    terms = {}
    for f in sorted((APP / "data" / "seed").glob("cpe_timetable_*.json")):
        d = load(f)
        terms[d["term"]] = d
        print(f"{d['term']}: {len(d['sections'])} หมู่เรียน")

    html = (HERE / "template.html").read_text(encoding="utf-8")
    if '"__TIMETABLE_DATA__"' not in html:
        raise SystemExit("ไม่พบ placeholder __TIMETABLE_DATA__ ใน template.html")

    body = html.replace('"__TIMETABLE_DATA__"',
                        json.dumps(terms, ensure_ascii=False, separators=(",", ":")))

    # template.html เป็นแค่เนื้อหน้า ไม่มี doctype/charset/viewport
    # GitHub Pages เสิร์ฟไฟล์ตรง ๆ จึงต้องประกอบเป็นเอกสารเต็มก่อน
    # ถ้าไม่มี charset ภาษาไทยจะกลายเป็นอักขระเพี้ยน และถ้าไม่มี viewport จอมือถือจะซูมออกจนอ่านไม่ออก
    out = (
        '<!doctype html>\n<html lang="th">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="จัดตารางเรียนวิศวกรรมคอมพิวเตอร์ มทร.ธัญบุรี '
        'แล้วตรวจให้ทันทีว่าเวลาเรียนชน เวลาสอบชน หน่วยกิตเกิน หรือยังไม่ผ่านวิชาบังคับก่อน">\n'
        '<style>html,body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        + body.split("</style>", 1)[0].split("<style>", 1)[0]     # <title> + <link> ของฟอนต์
        + "<style>" + body.split("<style>", 1)[1].split("</style>", 1)[0] + "</style>\n"
        + "</head>\n<body>\n"
        + body.split("</style>", 1)[1].lstrip()
        + "\n</body>\n</html>\n"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8")
    print(f"เขียน {OUT.relative_to(REPO_ROOT)} ขนาด {len(out.encode('utf-8')) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
