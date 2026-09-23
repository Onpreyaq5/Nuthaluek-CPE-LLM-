# -*- coding: utf-8 -*-
"""สร้างโฟลเดอร์สำรอง backup_project/ จากข้อมูลในรีโปเอง

    python ProJ-RMUTT-Planner/scripts/build_backup.py

ทำอะไร
  1. อ่านประวัติ git ทั้งหมด แล้วสรุปว่าใครทำอะไร โมดูลไหน ช่วงเวลาไหน
  2. เขียน backup_project/README.md (เปิดอ่านได้ทันทีบนหน้า GitHub)
  3. เขียน backup_project/ประวัติการพัฒนา.html (ตารางเต็ม เปิดในเบราว์เซอร์)
  4. คัดลอกเอกสารและเดโมจาก docs/ มาไว้ในโฟลเดอร์เดียวกัน
  5. เก็บสำเนาโปรเจกต์ทั้งก้อนและประวัติ git เป็นไฟล์เดียว (zip + bundle)

เก็บเป็นไฟล์บีบอัดแทนการคัดลอกไฟล์ทีละอัน เพราะถ้าคัดลอกตรง ๆ จะมีโค้ดสองชุด
ในรีโปเดียวกัน คนเปิดมาจะไม่รู้ว่าชุดไหนคือของจริง และทุกครั้งที่แก้โค้ดต้องตามแก้สองที่

ตัวเลขทุกตัวมาจาก git log ไม่ได้พิมพ์ทับเอง รันซ้ำเมื่อไหร่ก็ได้ผลตรงกับประวัติล่าสุดเสมอ
"""
from __future__ import annotations

import collections
import html
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # รากรีโป
OUT = ROOT / "backup_project"
SEP = "\x1f"

# ลิงก์เปิดใช้งานระบบ — แก้ตรงนี้เวลาลิงก์เปลี่ยน แล้วรันสคริปต์ใหม่
#
# ลิงก์ trycloudflare เป็นลิงก์ชั่วคราว ใช้ได้เฉพาะตอนเครื่องที่รัน Docker เปิดอยู่
# และเปลี่ยนใหม่ทุกครั้งที่สั่ง tunnel ขึ้น  ดูลิงก์ล่าสุดด้วย
#   docker compose --profile public logs tunnel_main | grep trycloudflare
PAGES_URL = "https://onpreyaq5.github.io/Nuthaluek-CPE-LLM-/"
LINKS = [
    ("แอปหลัก (09) — จัดตาราง ตรวจตารางชน ถามระเบียบ ไม่ต้องเข้าสู่ระบบ",
     "https://scientific-trips-recognize-sight.trycloudflare.com"),
    ("หน้าเว็บ CampusMate (01) — ระบบเต็ม เข้าสู่ระบบ admin / admin1234",
     "https://eclipse-formatting-retired-montgomery.trycloudflare.com"),
    ("หน้าเว็บ CampusMate (01) — ชุดเดิม",
     "https://broadband-potter-primary-guestbook.trycloudflare.com"),
    ("Grafana — กราฟเฝ้าดูระบบ เปิดดูได้โดยไม่ต้องเข้าสู่ระบบ",
     "https://lane-liberty-increasing-hotel.trycloudflare.com"),
]

# เอกสารที่คัดลอกมาเก็บไว้ในโฟลเดอร์สำรอง
COPIES = {
    "docs/architecture.pdf": "01_สถาปัตยกรรมระบบทั้งหมด.pdf",
    "docs/ch07-slides.pdf": "02_สไลด์บทที่7-RAG-LLM.pdf",
    "docs/index.html": "03_เดโมเปิดในเบราว์เซอร์ได้เลย.html",
}

MODULES = {
    "ProJ-RMUTT-Planner/01_web_app": "01 หน้าเว็บผู้ใช้",
    "ProJ-RMUTT-Planner/02_api_backend": "02 API / Backend",
    "ProJ-RMUTT-Planner/03_ai_router_agent": "03 AI Router / Agent",
    "ProJ-RMUTT-Planner/04_course_data_services": "04 ข้อมูลรายวิชา",
    "ProJ-RMUTT-Planner/05_data_integration": "05 ข้อมูลนักศึกษา",
    "ProJ-RMUTT-Planner/06_schedule_conflict_engine": "06 ตรวจตารางชน / จัดตาราง",
    "ProJ-RMUTT-Planner/07_rag_llm_engine": "07 RAG + LLM",
    "ProJ-RMUTT-Planner/08_recommendation_feedback": "08 สถิติและความเห็น",
    "ProJ-RMUTT-Planner/09_main_app": "09 แอปรวม",
    "ProJ-RMUTT-Planner/00_docs": "เอกสารประกอบ",
    "ProJ-RMUTT-Planner/infra": "โครงสร้างพื้นฐาน",
    "ProJ-RMUTT-Planner/scripts": "สคริปต์ตรวจสอบ",
    "ProJ-RMUTT-Planner/deploy": "การนำขึ้นใช้งาน",
    "docs": "หน้าเว็บเอกสาร",
    "LAB": "ใบงาน LAB",
}

TH_MONTH = {"01": "มกราคม", "02": "กุมภาพันธ์", "03": "มีนาคม", "04": "เมษายน",
            "05": "พฤษภาคม", "06": "มิถุนายน", "07": "กรกฎาคม", "08": "สิงหาคม",
            "09": "กันยายน", "10": "ตุลาคม", "11": "พฤศจิกายน", "12": "ธันวาคม"}


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def th_date(iso: str) -> str:
    """2026-07-15 -> 15 กรกฎาคม 2569"""
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {TH_MONTH[m]} {int(y) + 543}"


def module_of(path: str) -> str | None:
    if path.startswith("LAB"):
        return "LAB"
    for key in MODULES:
        if key != "LAB" and path.startswith(key + "/"):
            return key
    return None


# ── อ่านประวัติ ────────────────────────────────────────────────
def collect():
    commits = []
    for line in git("log", "--all", "--no-merges",
                    f"--format=%H{SEP}%an{SEP}%ad{SEP}%s", "--date=format:%Y-%m-%d %H:%M").splitlines():
        p = line.split(SEP)
        if len(p) == 4:
            commits.append({"sha": p[0][:7], "author": p[1], "date": p[2], "subject": p[3]})
    commits.sort(key=lambda c: c["date"])

    merges = []
    for line in git("log", "--all", "--merges",
                    f"--format=%an{SEP}%ad{SEP}%s", "--date=format:%Y-%m-%d").splitlines():
        p = line.split(SEP)
        if len(p) == 3:
            merges.append({"author": p[0], "date": p[1], "subject": p[2]})

    stats = collections.defaultdict(
        lambda: {"n": 0, "add": 0, "del": 0, "files": set(),
                 "modules": collections.Counter(), "first": None, "last": None})
    for c in commits:
        s = stats[c["author"]]
        s["n"] += 1
        s["first"] = c["date"] if s["first"] is None else min(s["first"], c["date"])
        s["last"] = c["date"] if s["last"] is None else max(s["last"], c["date"])

    author = None
    for line in git("log", "--all", "--no-merges", f"--format=@{SEP}%an", "--numstat").splitlines():
        if line.startswith("@" + SEP):
            author = line.split(SEP, 1)[1]
            continue
        if not author or "\t" not in line:
            continue
        a, d, path = (line.split("\t") + ["", "", ""])[:3]
        s = stats[author]
        if a.isdigit():
            s["add"] += int(a)
        if d.isdigit():
            s["del"] += int(d)
        s["files"].add(path)
        mod = module_of(path)
        if mod:
            s["modules"][mod] += 1

    months = collections.defaultdict(collections.Counter)
    for c in commits:
        months[c["date"][:7]][c["author"]] += 1

    branches = [b.strip().replace("remotes/origin/", "").replace("origin/", "")
                for b in git("branch", "-a").splitlines() if "->" not in b]
    branches = sorted(set(b.lstrip("* ").strip() for b in branches if b.strip()))
    return commits, merges, stats, months, branches


def main() -> None:
    commits, merges, stats, months, branches = collect()
    if not commits:
        raise SystemExit("อ่านประวัติ git ไม่ได้ — ต้องรันในรีโปที่ clone มาแบบมีประวัติครบ")

    ranked = sorted(stats.items(), key=lambda kv: -kv[1]["n"])
    OUT.mkdir(parents=True, exist_ok=True)

    for src, dst in COPIES.items():
        s = ROOT / src
        if s.exists():
            shutil.copy2(s, OUT / dst)

    # สำเนาโปรเจกต์ทั้งก้อน (เฉพาะไฟล์ที่ git เก็บ จึงไม่มี node_modules และไม่มี .env)
    zip_path = OUT / "โปรเจกต์ทั้งหมด.zip"
    zip_path.write_bytes(subprocess.run(
        ["git", "-C", str(ROOT), "archive", "--format=zip", "HEAD", "ProJ-RMUTT-Planner"],
        capture_output=True, check=True).stdout)

    # ประวัติ git ทั้งหมด: clone จากไฟล์นี้แล้วได้ทุกคอมมิตทุกสาขาครบ
    subprocess.run(["git", "-C", str(ROOT), "bundle", "create",
                    str(OUT / "ประวัติ-git-ทั้งหมด.bundle"), "--all"],
                   capture_output=True, check=True)

    total = len(commits) + len(merges)
    span = f"{th_date(commits[0]['date'])} – {th_date(commits[-1]['date'])}"

    # ── README.md ────────────────────────────────────────────
    # ตั้งใจไม่ใส่ตารางประวัติลงหน้านี้ ให้หน้านี้เป็นทางเข้าใช้งานล้วน ๆ
    # ใครอยากดูประวัติเปิดไฟล์ ประวัติการพัฒนา.html หรือ .pdf ได้
    lines = [
        "# สำรองงานทั้งหมด — RMUTT Study Planner",
        "",
        "ระบบวางแผนการเรียน มหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี",
        "",
        "## เปิดใช้งานระบบจริง",
        "",
        "| เปิดอะไร | ลิงก์ |",
        "|---|---|",
    ]
    for label, url in LINKS:
        lines.append(f"| {label} | {url} |")
    lines += [
        f"| เอกสารทั้งหมดในรูปแบบเว็บ (GitHub Pages) | {PAGES_URL} |",
        "",
        "> ลิงก์ `trycloudflare.com` เป็นลิงก์ชั่วคราว ใช้ได้เฉพาะตอนเครื่องที่รัน Docker เปิดอยู่",
        "> และเปลี่ยนใหม่ทุกครั้งที่สั่งขึ้น ถ้าเปิดไม่ได้ให้รันระบบเองตามหัวข้อด้านล่าง",
        "",
        "## รันระบบเองด้วย Docker",
        "",
        "```bash",
        "cd ProJ-RMUTT-Planner",
        "cp .env.example .env",
        "docker compose up -d --build        # เปิด http://localhost:3000",
        "bash scripts/verify_docker.sh       # ตรวจทุกบริการว่าทำงานจริง",
        "```",
        "",
        "หน้าเว็บ CampusMate ตัวเต็มพร้อมทุกบริการที่เรียกใช้:",
        "",
        "```bash",
        "docker compose -f deploy/webapp/docker-compose.yml --env-file .env up -d --build",
        "python deploy/webapp/verify.py      # เปิด http://localhost:4001",
        "```",
        "",
        "## ไฟล์ในโฟลเดอร์นี้",
        "",
        "| ไฟล์ | เนื้อหา |",
        "|---|---|",
        "| `01_สถาปัตยกรรมระบบทั้งหมด.pdf` | ภาพรวม 9 โมดูล Use Case มายด์แมป ลำดับการทำงาน |",
        "| `02_สไลด์บทที่7-RAG-LLM.pdf` | สไลด์ 16:9 เรื่องการค้นคืนเอกสารและ LLM |",
        "| `03_เดโมเปิดในเบราว์เซอร์ได้เลย.html` | ไฟล์เดียวจบ ดับเบิลคลิกใช้งานได้ ไม่ต้องติดตั้งอะไร |",
        "| `ประวัติการพัฒนา.html` · `.pdf` | ผลงานรายคน ใครทำโมดูลไหน และคอมมิตทุกรายการ |",
        "| `โปรเจกต์ทั้งหมด.zip` | สำเนาโค้ดทั้งโปรเจกต์ ไม่มี node_modules ไม่มีคีย์ |",
        "| `ประวัติ-git-ทั้งหมด.bundle` | ประวัติ git ครบทุกคอมมิตทุกสาขา |",
        "",
        "## กู้คืนจากไฟล์สำรอง",
        "",
        "```bash",
        "git clone ประวัติ-git-ทั้งหมด.bundle rmutt-planner   # ได้ประวัติครบทุกคน",
        "unzip โปรเจกต์ทั้งหมด.zip                              # หรือเอาแค่ไฟล์",
        "```",
        "",
        "---",
        "",
        f"สร้างไฟล์ในโฟลเดอร์นี้ใหม่: `python ProJ-RMUTT-Planner/scripts/build_backup.py`",
        f"({total} คอมมิต · {len(ranked)} คน · {len(branches)} สาขา · {span})",
        "",
        "เอกสารระเบียบ หลักสูตร ปฏิทินการศึกษา และตารางสอนในระบบนี้",
        "**เป็นข้อมูลจำลองสำหรับต้นแบบ** ไม่ใช่ข้อมูลจริงของมหาวิทยาลัย",
        "",
    ]
    (OUT / "README.md").write_text("\n".join(lines), encoding="utf-8")

    # ── ประวัติการพัฒนา.html ──────────────────────────────────
    def esc(x: object) -> str:
        return html.escape(str(x))

    max_month = max(sum(c.values()) for c in months.values())
    people = "\n".join(
        f"<tr><td class=name>{esc(a)}</td><td class=num>{s['n']}</td>"
        f"<td class='num add'>+{s['add']:,}</td><td class='num del'>-{s['del']:,}</td>"
        f"<td class=num>{len(s['files']):,}</td>"
        f"<td class=small>{esc(', '.join(MODULES[m] for m, _ in s['modules'].most_common(3)))}</td>"
        f"<td class=date>{esc(s['first'][:10])} – {esc(s['last'][:10])}</td></tr>"
        for a, s in ranked)
    month_rows = "\n".join(
        f"<tr><td class=date>{TH_MONTH[ym.split('-')[1]]} {int(ym.split('-')[0]) + 543}</td>"
        f"<td class=num>{sum(c.values())}</td>"
        f"<td><div class=bar style='width:{sum(c.values()) / max_month * 100:.0f}%'></div></td>"
        f"<td class=small>{esc(', '.join(f'{n} ({k})' for n, k in c.most_common()))}</td></tr>"
        for ym, c in sorted(months.items()))
    merge_rows = "\n".join(
        f"<tr><td class=date>{esc(m['date'])}</td><td class=name>{esc(m['author'])}</td>"
        f"<td>{esc(m['subject'])}</td></tr>" for m in merges)
    log_rows = "\n".join(
        f"<tr><td class=date>{esc(c['date'])}</td><td class=sha>{esc(c['sha'])}</td>"
        f"<td class=name>{esc(c['author'])}</td><td>{esc(c['subject'])}</td></tr>"
        for c in reversed(commits))

    (OUT / "ประวัติการพัฒนา.html").write_text(f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ประวัติการพัฒนา — RMUTT Study Planner</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap">
<style>
 :root{{--ink:#101828;--ink2:#475467;--line:#DCE3EE;--brand:#1D4ED8;
       --ok:#0B7F5B;--bad:#B3324A;--soft:#F2F5FA}}
 *{{box-sizing:border-box}}
 body{{margin:0 auto;padding:32px 40px;max-width:1100px;color:var(--ink);line-height:1.6;
      font-family:"IBM Plex Sans Thai",system-ui,sans-serif}}
 h1{{font-size:30px;margin:0 0 4px}}
 h2{{font-size:20px;margin:34px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--line)}}
 .sub{{color:var(--ink2);margin-bottom:22px}}
 .cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}}
 .card{{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:14px 16px}}
 .card b{{display:block;font-size:26px;color:var(--brand);font-variant-numeric:tabular-nums}}
 .card span{{font-size:13px;color:var(--ink2)}}
 table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px}}
 th{{text-align:left;font-size:12px;color:var(--ink2);background:var(--soft);
     padding:8px 10px;border-bottom:1px solid var(--line);font-weight:600}}
 td{{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
 .num{{text-align:right;font-family:"IBM Plex Mono",monospace;white-space:nowrap}}
 .add{{color:var(--ok)}} .del{{color:var(--bad)}}
 .date{{font-family:"IBM Plex Mono",monospace;font-size:12.5px;color:var(--ink2);white-space:nowrap}}
 .sha{{font-family:"IBM Plex Mono",monospace;font-size:12.5px;color:var(--brand)}}
 .name{{font-weight:600;white-space:nowrap}} .small{{font-size:12.5px;color:var(--ink2)}}
 .bar{{height:9px;background:var(--brand);border-radius:99px;min-width:3px}}
 .tags span{{display:inline-block;background:var(--soft);border:1px solid var(--line);
   border-radius:99px;padding:3px 11px;font-size:12.5px;margin:3px 4px 0 0;
   font-family:"IBM Plex Mono",monospace}}
 @media print{{@page{{size:A4;margin:14mm}} body{{padding:0}}
   h2{{break-after:avoid}} tr{{break-inside:avoid}}}}
</style></head><body>
<h1>ประวัติการพัฒนา</h1>
<div class=sub>ระบบวางแผนการเรียน มทร.ธัญบุรี — RMUTT Study Planner<br>
ทุกตัวเลขดึงจากประวัติ git โดยตรง ตรวจย้อนได้ด้วย <code>git log</code></div>
<div class=cards>
 <div class=card><b>{total}</b><span>คอมมิตทั้งหมด</span></div>
 <div class=card><b>{len(ranked)}</b><span>ผู้ร่วมพัฒนา</span></div>
 <div class=card><b>{len(branches)}</b><span>สาขา</span></div>
 <div class=card><b>{len(merges)}</b><span>การรวมงาน</span></div>
</div>
<h2>ผลงานรายบุคคล</h2>
<table><tr><th>ผู้พัฒนา</th><th class=num>คอมมิต</th><th class=num>เพิ่ม</th><th class=num>ลบ</th>
<th class=num>ไฟล์</th><th>โมดูลหลักที่รับผิดชอบ</th><th>ช่วงเวลา</th></tr>
{people}</table>
<h2>ความเคลื่อนไหวรายเดือน</h2>
<table><tr><th>เดือน</th><th class=num>คอมมิต</th><th style="width:24%"></th><th>ผู้พัฒนา</th></tr>
{month_rows}</table>
<h2>สาขาที่ใช้พัฒนา</h2>
<div class=tags>{''.join(f'<span>{esc(b)}</span>' for b in branches)}</div>
<h2>การรวมงานเข้าสาขาหลัก</h2>
<table><tr><th>วันที่</th><th>ผู้รวม</th><th>รายละเอียด</th></tr>{merge_rows}</table>
<h2>บันทึกคอมมิตทั้งหมด</h2>
<table><tr><th>วันที่และเวลา</th><th>รหัส</th><th>ผู้พัฒนา</th><th>รายละเอียด</th></tr>
{log_rows}</table>
</body></html>
""", encoding="utf-8")

    print(f"เขียน {OUT.relative_to(ROOT)}/ แล้ว")
    for f in sorted(OUT.iterdir()):
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")
    print(f"\n{total} คอมมิต · {len(ranked)} คน · {len(branches)} สาขา · {span}")


if __name__ == "__main__":
    main()
