"""ทดสอบทุกฟีเจอร์ของหน้าเว็บ 01 ผ่านทางเดียวกับเบราว์เซอร์ (nginx ของ 01 -> 02 -> 03..08)

    python deploy/webapp/verify.py                       # http://localhost:4001
    python deploy/webapp/verify.py https://xxxx.trycloudflare.com

ใช้แค่ standard library รันได้ทุกเครื่องที่มี Python 3.10+
ออกด้วยรหัส 0 เมื่อผ่านหมด
"""
from __future__ import annotations

import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:4001").rstrip("/")
TERM = "1/2569"
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, name: str, detail: str = "") -> bool:
    RESULTS.append((ok, name))
    mark = "\033[32mผ่าน\033[0m" if ok else "\033[31mตก  \033[0m"
    print(f"  {mark}  {name}" + (f"  — {detail}" if detail else ""))
    return ok


def call(method: str, path: str, body=None, raw: bytes | None = None,
         ctype: str = "application/json", timeout: int = 60):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(BASE + "/api/v1" + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", ctype)
    try:
        with OPENER.open(req, timeout=timeout) as r:
            text, code = r.read().decode("utf-8", "replace"), r.status
    except urllib.error.HTTPError as e:
        text, code = e.read().decode("utf-8", "replace"), e.code
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}
    try:
        return code, json.loads(text)
    except ValueError:
        return code, text


def data_of(resp) -> dict:
    return resp.get("data") or {} if isinstance(resp, dict) else {}


def chat(message: str) -> dict:
    """ส่งข้อความแชตแล้วรวม event SSE เป็น {text, sources, types, seconds}"""
    t0 = time.time()
    req = urllib.request.Request(BASE + "/api/v1/chat", data=json.dumps({"message": message}).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    try:
        raw = OPENER.open(req, timeout=200).read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return {"text": "", "sources": [], "types": ["error"], "seconds": time.time() - t0, "error": str(e)}
    events = [json.loads(l[6:]) for l in raw.splitlines() if l.startswith("data: ")]
    return {
        "text": "".join(e.get("text", "") for e in events if e.get("type") == "token"),
        "sources": [s.get("title") for e in events if e.get("type") == "sources" for s in e.get("items", [])],
        "types": [e.get("type") for e in events],
        "seconds": time.time() - t0,
    }


def main() -> int:
    print(f"\nทดสอบหน้าเว็บ 01 ที่ {BASE}\n")

    print("1. หน้าเว็บและการเข้าสู่ระบบ")
    try:
        html = urllib.request.urlopen(BASE + "/", timeout=20).read().decode("utf-8", "replace")
        check("<div id=\"root\">" in html or "<!doctype html" in html.lower(), "เปิดหน้าเว็บได้")
    except Exception as e:  # noqa: BLE001
        check(False, "เปิดหน้าเว็บได้", str(e))
        return 1
    code, _ = call("POST", "/auth/login", {"username": "admin", "password": "admin1234"})
    if not check(code == 200, "login บัญชีเดโม", f"HTTP {code}"):
        return 1

    print("\n2. ค้นรายวิชา (ข้อมูลตารางสอนจริง)")
    code, r = call("GET", f"/courses?term={TERM.replace('/', '%2F')}&limit=100")
    courses = data_of(r).get("items") or []
    check(code == 200 and len(courses) >= 20, "ค้นรายวิชาทั้งหมด", f"{len(courses)} วิชา")
    code, r = call("GET", f"/courses?term={TERM.replace('/', '%2F')}&day=MON")
    check(code == 200, "กรองตามวัน (จันทร์)", f"HTTP {code}")
    sections = []
    for c in courses:
        _, s = call("GET", f"/courses/{c['code']}/sections?term={TERM.replace('/', '%2F')}")
        sections += data_of(s).get("items") or []
    check(len(sections) >= len(courses), "ดูกลุ่มเรียนของทุกวิชา", f"{len(sections)} กลุ่มเรียน")

    print("\n3. จัดตารางเรียน / ตรวจตารางชน")
    clash = None
    seen: dict[tuple[str, str], dict] = {}
    for s in sections:
        for m in s["meetings"]:
            k = (m["day"], m["start"])
            if k in seen and seen[k]["course_code"] != s["course_code"]:
                clash = (seen[k]["section_id"], s["section_id"])
                break
            seen.setdefault(k, s)
        if clash:
            break
    if check(clash is not None, "หาคู่กลุ่มเรียนที่เวลาทับกันในข้อมูลจริง", str(clash)):
        code, r = call("POST", "/plans/validate", {"term": TERM, "section_ids": list(clash)})
        types = [c.get("type") for c in data_of(r).get("conflicts", [])]
        check(code == 200 and "time_clash" in types, "ตรวจชนเจอเวลาเรียนทับกัน", ", ".join(types))

    code, r = call("POST", "/plans/auto", {"term": TERM, "preferences": {
        "free_days": ["FRI"], "no_early_class": False, "max_credits": 21}}, timeout=90)
    plans = data_of(r).get("plans") or []
    check(code == 200 and len(plans) > 0, "จัดตารางอัตโนมัติ",
          f"{len(plans)} แผน" + (f", แผนแรก {plans[0].get('total_credits')} หน่วยกิต" if plans else ""))

    sid = sections[0]["section_id"]
    code, r = call("POST", "/plans", {"term": TERM, "name": "verify", "section_ids": [sid]})
    pid = data_of(r).get("plan_id") or data_of(r).get("id")
    check(code == 200 and pid is not None, "บันทึกแผน", f"plan_id={pid}")
    if pid:
        code, r = call("GET", f"/plans/{pid}/explain", timeout=90)
        exp = data_of(r).get("explanation", "")
        check(code == 200 and len(exp) > 20 and "****" not in exp, "อธิบายแผนด้วย AI", exp[:60].replace("\n", " "))
        code, _ = call("POST", "/feedback", {"target_type": "plan", "target_id": str(pid), "rating": 5, "reason": ""})
        check(code == 200, "ส่ง feedback (ไปที่ 08)", f"HTTP {code}")
        code, _ = call("DELETE", f"/plans/{pid}")
        check(code == 200, "ลบแผน", f"HTTP {code}")

    print("\n4. โปรไฟล์และนำเข้าผลการเรียน")
    code, _ = call("GET", "/students/me/profile")
    check(code == 200, "ดูโปรไฟล์", f"HTTP {code}")
    code, _ = call("GET", "/students/me/transcript")
    check(code == 200, "ดู transcript (ยังไม่นำเข้า = ว่าง ไม่ใช่ error)", f"HTTP {code}")
    sample = urllib.request.urlopen(BASE + "/sample-transcript.html", timeout=20).read()
    crlf = "\r\n"
    boundary = "----rmutt-verify"
    head = (f"--{boundary}{crlf}Content-Disposition: form-data; name=\"file\"; filename=\"t.html\"{crlf}"
            f"Content-Type: text/html{crlf}{crlf}")
    body = head.encode() + sample + f"{crlf}--{boundary}--{crlf}".encode()
    code, r = call("POST", "/students/me/import", raw=body, ctype=f"multipart/form-data; boundary={boundary}")
    n = data_of(r).get("imported_courses", 0)
    check(code == 200 and n > 0, "นำเข้าไฟล์ตรวจสอบจบตัวอย่าง", f"{n} วิชา")
    _, r = call("GET", "/students/me/transcript")
    check(len(data_of(r).get("courses") or []) > 0, "transcript มีวิชาหลังนำเข้า",
          f"{len(data_of(r).get('courses') or [])} วิชา")

    print("\n5. แชต AI (หน้าเว็บ -> API -> AI Router -> RAG / Gemini / เครื่องมือ)")
    r = chat("ถอนรายวิชาได้ถึงเมื่อไหร่")
    check("done" in r["types"] and "ข้อ 18" in r["text"] + " ".join(r["sources"]) or
          "ข้อบังคับ" in " ".join(r["sources"]),
          "ถามระเบียบ ได้คำตอบพร้อมแหล่งอ้างอิง", f"{r['seconds']:.1f}s, {len(r['sources'])} แหล่ง")
    r = chat("วิชา 04100203-66 ต้องผ่านวิชาอะไรมาก่อน")
    check("04100103-66" in r["text"], "ถามวิชาบังคับก่อนด้วยรหัสวิชาจริง", f"{r['seconds']:.1f}s")
    if clash:
        r = chat(f"{clash[0]} กับ {clash[1]} ชนกันไหม")
        check("C1" in r["text"], "ถามตารางชนในแชต (ใช้ระบบตรวจชน ไม่ให้ AI เดา)", f"{r['seconds']:.1f}s")
    r = chat("ช่วยเขียนอีเมลขอลาป่วยถึงอาจารย์สั้นๆ ให้หน่อย")
    check("done" in r["types"] and len(r["text"]) > 40, "คำถามทั่วไป (General AI)", f"{r['seconds']:.1f}s")
    code, r = call("GET", "/chat/sessions")
    check(code == 200 and len(data_of(r).get("items") or []) > 0, "ประวัติแชตถูกบันทึก",
          f"{len(data_of(r).get('items') or [])} บทสนทนา")

    passed = sum(ok for ok, _ in RESULTS)
    failed = len(RESULTS) - passed
    print(f"\nสรุป  ผ่าน {passed} · ตก {failed}")
    for ok, name in RESULTS:
        if not ok:
            print(f"  ตก: {name}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
