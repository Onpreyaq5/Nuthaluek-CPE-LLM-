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

import ast
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


def load_knowledge() -> dict[str, str]:
    """คลังความรู้ของ RAG — ฝังทั้งไฟล์ลงหน้าเว็บ เบราว์เซอร์จะสร้างดัชนีเองตอนเปิดแท็บถาม-ตอบ"""
    folder = APP / "data" / "knowledge"
    out = {}
    for path in sorted(folder.glob("*.md")):
        out[path.name] = path.read_text(encoding="utf-8")
    return out


def load_golden_set() -> dict[str, list[str]]:
    """ดึงชุดคำถามมาตรฐานจากไฟล์เทสจริงของโมดูล 07

    ทำไมต้องดึงจากเทส ไม่ copy มาวางไว้เอง: ถ้าแยกกันเก็บ วันหนึ่งจะหลุดจากกัน
    แล้วหน้าเว็บจะโชว์ผลของชุดคำถามคนละชุดกับที่ CI รันจริง ซึ่งแย่กว่าไม่โชว์เลย
    """
    test_file = APP.parent / "07_rag_llm_engine" / "tests" / "test_retrieval.py"
    tree = ast.parse(test_file.read_text(encoding="utf-8"))
    found: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("ON_TOPIC", "OFF_TOPIC"):
                found[name.lower()] = list(ast.literal_eval(node.value))
    missing = {"on_topic", "off_topic"} - set(found)
    if missing:
        raise SystemExit(f"หา {missing} ใน {test_file.name} ไม่เจอ — โครงไฟล์เทสเปลี่ยนไปแล้ว")
    return found


def load_proxy_url() -> str:
    """URL ของตัวกลางที่ถือคีย์ Gemini ไว้ฝั่งเซิร์ฟเวอร์

    หน้าเว็บนิ่งซ่อนคีย์ไม่ได้ ใครกด View Source ก็เห็น จึงห้ามฝังคีย์ลงหน้าเว็บเด็ดขาด
    วิธีที่ได้ผลคือ deploy 09_main_app ขึ้น Vercel แล้วเก็บคีย์ไว้ใน env ที่นั่น
    หน้านี้ยิงคำถามไปที่ /api/chat ของตัวนั้น ผู้ใช้จึงได้คำตอบจาก Gemini
    โดยไม่เคยเห็นและไม่ต้องกรอกคีย์เลย
    """
    cfg = HERE / "config.json"
    if not cfg.exists():
        return ""
    # utf-8-sig เพราะโปรแกรมแก้ไฟล์บน Windows (รวมถึง PowerShell) มักเขียน BOM นำหน้ามาด้วย
    # แล้ว json.loads จะพังทันทีโดยที่คนแก้ไม่รู้ว่าพิมพ์อะไรผิด
    url = (json.loads(cfg.read_text(encoding="utf-8-sig")).get("llm_proxy_url") or "").strip()
    return url.rstrip("/")


def main() -> None:
    terms = {}
    for f in sorted((APP / "data" / "seed").glob("cpe_timetable_*.json")):
        d = load(f)
        terms[d["term"]] = d
        print(f"{d['term']}: {len(d['sections'])} หมู่เรียน")

    html = (HERE / "template.html").read_text(encoding="utf-8")
    if '"__TIMETABLE_DATA__"' not in html:
        raise SystemExit("ไม่พบ placeholder __TIMETABLE_DATA__ ใน template.html")

    knowledge = load_knowledge()
    golden = load_golden_set()
    print(f"คลังความรู้: {len(knowledge)} ไฟล์ "
          f"({sum(len(v) for v in knowledge.values()) / 1024:.0f} KB)")
    print(f"ชุดคำถามมาตรฐาน: ตอบได้ {len(golden['on_topic'])} ข้อ / "
          f"นอกเรื่อง {len(golden['off_topic'])} ข้อ")

    def dump(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    proxy = load_proxy_url()
    print(f"ตัวกลาง LLM: {proxy or '(ยังไม่ได้ตั้ง — จะใช้โหมดอ้างเอกสารตรง)'}")

    body = html.replace('"__TIMETABLE_DATA__"', dump(terms))
    body = body.replace('"__LLM_PROXY_URL__"', dump(proxy))
    for placeholder, value in (("__KNOWLEDGE_DATA__", knowledge), ("__GOLDEN_SET__", golden)):
        if f'"{placeholder}"' not in body:
            raise SystemExit(f"ไม่พบ placeholder {placeholder} ใน template.html")
        body = body.replace(f'"{placeholder}"', dump(value))

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
