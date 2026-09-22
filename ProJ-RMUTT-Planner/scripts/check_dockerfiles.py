"""ตรวจ Dockerfile หาปัญหาที่ทำให้ container พังหรือค้าง ตอนรันจริงเท่านั้น

    python ProJ-RMUTT-Planner/scripts/check_dockerfiles.py

ปัญหาที่ดักไว้ — ทุกข้อ build ผ่านปกติ จะรู้ตัวก็ตอนรันแล้ว

  HEALTHCHECK เรียก curl/wget แต่ image ไม่ได้ติดตั้ง
      healthcheck จะล้มเหลวตลอด container ขึ้นสถานะ unhealthy ถาวร
      บริการที่รอด้วย condition: service_healthy จะค้างรอไม่จบ

  ไฟล์ .sh ที่ถูก COPY แล้วลงท้ายบรรทัดด้วย CRLF
      shebang กลายเป็น "#!/bin/sh\\r" ซึ่ง Linux หา interpreter ไม่เจอ
      ขึ้น exec format error หรือ no such file or directory ที่งงมาก

  ENTRYPOINT/CMD ชี้ไปสคริปต์ที่ไม่ได้ COPY เข้ามา หรือไม่ได้ chmod +x

  พอร์ตใน EXPOSE/CMD ไม่ตรงกับที่ compose map ไว้
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))

problems: list[str] = []
notes: list[str] = []

# เครื่องมือที่ต้องมีในภาพถึงจะใช้ใน HEALTHCHECK ได้
TOOL_INSTALLERS = {
    "curl": ("apt-get install", "apk add", "apt install"),
    "wget": ("apt-get install", "apk add", "apt install"),
}


def service_for(context: Path, dockerfile: str) -> tuple[str, dict] | tuple[None, None]:
    for name, spec in (compose.get("services") or {}).items():
        b = (spec or {}).get("build")
        if not b:
            continue
        ctx = ROOT / (b if isinstance(b, str) else b.get("context", "."))
        dfn = "Dockerfile" if isinstance(b, str) else b.get("dockerfile", "Dockerfile")
        if ctx.resolve() == context.resolve() and dfn == dockerfile:
            return name, spec
    return None, None


def check(df: Path) -> None:
    text = df.read_text(encoding="utf-8")
    context = df.parent
    svc, spec = service_for(context, df.name)
    label = f"{context.name}/{df.name}"

    # ── HEALTHCHECK ใช้เครื่องมือที่ไม่ได้ติดตั้ง ──
    hc = re.search(r"^HEALTHCHECK[\s\S]*?(?=\n[A-Z]|\Z)", text, re.MULTILINE)
    if hc:
        body = hc.group(0)
        for tool, installers in TOOL_INSTALLERS.items():
            if re.search(rf"\b{tool}\b", body):
                installed = any(inst in text and tool in text.split(inst, 1)[1][:400]
                                for inst in installers)
                # node:alpine / python:slim ไม่มี curl มาให้
                if not installed:
                    problems.append(
                        f"{label}: HEALTHCHECK เรียก {tool} แต่ Dockerfile ไม่ได้ติดตั้ง "
                        f"-> healthcheck ล้มเหลวตลอด บริการที่รอ service_healthy จะค้าง")

    # ── ไฟล์ .sh ที่ COPY เข้ามา ต้องไม่เป็น CRLF และต้อง chmod +x ──
    for m in re.finditer(r"^COPY\s+(?!--from)(\S+\.sh)\s", text, re.MULTILINE):
        rel = m.group(1)
        f = context / rel
        if not f.exists():
            problems.append(f"{label}: COPY {rel} แต่ไม่มีไฟล์นี้")
            continue
        raw = f.read_bytes()
        if b"\r\n" in raw and "sed -i 's/\\r$//'" not in text and 'sed -i "s/\\r$//"' not in text:
            problems.append(
                f"{label}: {rel} ลงท้ายบรรทัดเป็น CRLF และ Dockerfile ไม่ได้ตัด \\r ออก "
                f"-> shebang พัง ขึ้น exec format error")
        if f"chmod +x {rel}" not in text and "chmod +x" not in text:
            notes.append(f"{label}: {rel} ไม่เห็นคำสั่ง chmod +x (ถ้าสิทธิ์ติดมาจาก git อยู่แล้วก็ผ่าน)")

    # ── ENTRYPOINT/CMD ชี้ไปสคริปต์ที่ต้องมีจริง ──
    for kw in ("ENTRYPOINT", "CMD"):
        m = re.search(rf"^{kw}\s+(\[.*\])\s*$", text, re.MULTILINE)
        if not m:
            continue
        try:
            argv = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        first = argv[0] if argv else ""
        if first.startswith("./") or first.endswith(".sh"):
            target = context / first.lstrip("./")
            if not target.exists():
                problems.append(f"{label}: {kw} เรียก {first} แต่ไม่มีไฟล์นี้ใน build context")

        # ── พอร์ตใน CMD ต้องตรงกับที่ compose map ──
        if spec:
            ports = [str(p).split(":") for p in (spec.get("ports") or [])]
            inner = {p[-1].strip('"') for p in ports if p}
            in_cmd = {a for a in argv if re.fullmatch(r"\d{2,5}", str(a))}
            if inner and in_cmd and not (in_cmd & inner):
                problems.append(
                    f"{label}: {kw} ฟังที่พอร์ต {sorted(in_cmd)} แต่ compose map "
                    f"ไปที่ {sorted(inner)} -> เข้าไม่ถึงบริการ")

    # ── EXPOSE ควรตรงกับพอร์ตที่ compose ใช้ ──
    exposed = set(re.findall(r"^EXPOSE\s+(\d+)", text, re.MULTILINE))
    if spec and exposed:
        inner = {str(p).split(":")[-1].strip('"') for p in (spec.get("ports") or [])}
        if inner and not (exposed & inner):
            notes.append(f"{label}: EXPOSE {sorted(exposed)} ไม่ตรงกับ compose {sorted(inner)}")

    print(f"  ตรวจแล้ว {label:44} -> บริการ {svc or '(ไม่ได้ใช้ใน compose)'}")


print("ตรวจ Dockerfile ทั้งหมด\n")
for df in sorted(ROOT.glob("*/Dockerfile*")):
    if df.name.endswith((".dev", ".md")) or "Dockerfile.dev" == df.name:
        continue
    check(df)

print()
for n in notes:
    print(f"  หมายเหตุ: {n}")
if problems:
    print(f"\nพบปัญหา {len(problems)} ข้อ")
    for p in problems:
        print(f"  ! {p}")
    sys.exit(1)
print("\nผ่านทุกข้อ — ไม่พบจุดที่จะทำให้ container พังหรือค้างตอนรัน")
