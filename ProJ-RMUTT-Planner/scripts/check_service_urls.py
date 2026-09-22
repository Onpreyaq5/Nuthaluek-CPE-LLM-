"""หา URL ภายในที่โค้ดตั้งไว้ แล้วเทียบกับชื่อบริการจริงใน docker-compose

    python ProJ-RMUTT-Planner/scripts/check_service_urls.py

ถ้าโค้ดชี้ไปที่ host ที่ไม่มีใน compose = ใน container จะเรียกไม่ติด
และจะเจอก็ต่อเมื่อรันจริงแล้วลองยิง ไม่ใช่ตอน build
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
services = set(compose["services"])
# ชื่อที่ต่อได้จริงใน network: ชื่อบริการ + container_name + aliases
hosts_ok = set(services)
for name, spec in compose["services"].items():
    cn = (spec or {}).get("container_name")
    if cn:
        hosts_ok.add(cn)

URL_PAT = re.compile(r"https?://([a-zA-Z0-9_.-]+)(?::(\d+))?")
SKIP_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "example.com", "oreg3.rmutt.ac.th",
              "www.rmutt.ac.th", "generativelanguage.googleapis.com", "api.openai.com",
              "api.anthropic.com", "docs.github.com", "github.com", "aistudio.google.com",
              "fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net",
              "cdnjs.cloudflare.com", "onpreyaq5.github.io", "claude.ai", "canva.com",
              "raw.githubusercontent.com", "www.canva.com", "support.github.com",
              "docs.pytest.org", "www.githubstatus.com", "host.docker.internal"}

print(f"บริการใน compose: {', '.join(sorted(services))}\n")
print(f"{'โมดูล':30} {'host ที่โค้ดชี้ไป':34} {'พอร์ต':>6}  ผล")
print("-" * 96)

problems = []
for mod in sorted(ROOT.glob("0[1-9]_*")):
    seen = {}
    for p in list(mod.rglob("*.py")) + list(mod.rglob("*.ts")) + list(mod.rglob("*.tsx")):
        s = p.as_posix()
        if "__pycache__" in s or "node_modules" in s or "/tests/" in s:
            continue
        for m in URL_PAT.finditer(p.read_text(encoding="utf-8", errors="replace")):
            host, port = m.group(1), m.group(2) or ""
            if host in SKIP_HOSTS or "." in host and not host.endswith(("_", "-")):
                if host in SKIP_HOSTS:
                    continue
            if host in SKIP_HOSTS:
                continue
            seen.setdefault((host, port), p.relative_to(ROOT).as_posix())
    for (host, port), where in sorted(seen.items()):
        if "." in host:          # โดเมนภายนอก ข้าม
            continue
        ok = host in hosts_ok
        mark = "ต่อได้" if ok else "!! ไม่มีบริการชื่อนี้ใน compose"
        print(f"{mod.name:30} {host:34} {port:>6}  {mark}")
        if not ok:
            problems.append((mod.name, host, port, where))

print()
if problems:
    print(f"พบ host ที่เรียกไม่ติด {len(problems)} จุด:")
    for mod, host, port, where in problems:
        print(f"  ! {mod}: ชี้ไป {host}:{port}  ({where})")
else:
    print("ทุก host ที่โค้ดชี้ไป มีบริการรองรับใน compose ครบ")

raise SystemExit(1 if problems else 0)
