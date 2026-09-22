"""ตรวจ docker-compose.yml ว่าพร้อมรันจริงไหม โดยไม่ต้องมี Docker ในเครื่อง

    python ProJ-RMUTT-Planner/scripts/check_compose.py

ตรวจสิ่งที่ `docker compose up` จะเจอเป็นอย่างแรก ๆ และพังทันทีถ้าผิด
  - YAML แตกไหม
  - build context และ Dockerfile มีจริงไหม
  - ไฟล์ที่ Dockerfile สั่ง COPY มีจริงไหม  (สาเหตุ build พังที่เจอบ่อยที่สุด)
  - ตัวแปรที่ compose ใช้ มีใน .env.example ครบไหม
  - พอร์ตชนกันเองไหม
  - depends_on ชี้ไปหาบริการที่มีจริงไหม และบริการปลายทางมี healthcheck ไหม
    (ถ้าใช้ condition: service_healthy แต่ปลายทางไม่มี healthcheck compose จะรอค้าง)

ใช้ได้ทั้งในเครื่องและใน CI จึงไม่ต้องรอให้ใครมีเครื่องที่ลง Docker ก่อน
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("ต้องมี PyYAML ก่อน:  pip install pyyaml")

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
ENV_EXAMPLE = ROOT / ".env.example"

problems: list[str] = []
notes: list[str] = []
TRACKED: set[str] | None = None


def check_dockerfile_copies(service: str, context: Path, dockerfile: Path,
                            optional: bool = False) -> None:
    """ไฟล์ที่ COPY ต้องมีจริง ไม่งั้น build พังกลางทาง

    optional=True สำหรับบริการที่อยู่หลัง profile ซึ่งไม่ขึ้นตอน `docker compose up`
    ปัญหาของมันจึงไม่ทำให้คำสั่งปกติพัง แค่ต้องรู้ไว้ก่อนจะเปิด profile นั้น
    """
    bucket = notes if optional else problems
    for line in dockerfile.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*COPY\s+(?!--from)(.+?)\s+\S+\s*$", line)
        if not m:
            continue
        for src in m.group(1).split():
            if src.startswith("--"):
                continue
            hit = list(context.glob(src)) if "*" in src else [context / src]
            if not any(p.exists() for p in hit):
                bucket.append(f"{service}: {dockerfile.name} สั่ง COPY {src} แต่ไม่มีใน "
                              f"{context.name}/ — build จะพังเมื่อเปิด profile นี้"
                              if optional else
                              f"{service}: {dockerfile.name} สั่ง COPY {src} แต่ไม่มีใน {context.name}/")


def tracked_paths() -> set[str] | None:
    """ไฟล์ที่ git เก็บจริง

    ไฟล์ที่มีแค่ในเครื่องแต่ git ไม่ได้เก็บ (เช่นโฟลเดอร์ว่าง) จะหายไปตอน CI checkout
    แล้ว docker build พังเฉพาะบน CI ซึ่งหาสาเหตุยากกว่าพังในเครื่องมาก
    """
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT.parent, capture_output=True,
                             text=True, timeout=30, check=True).stdout
    except Exception:
        return None
    return {line.strip() for line in out.splitlines() if line.strip()}


def check_untracked_dirs(service: str, context: Path, optional: bool = False) -> None:
    """โฟลเดอร์ที่มีในเครื่องแต่ git ไม่ได้เก็บไฟล์ไหนเลย

    git ไม่เก็บโฟลเดอร์ว่าง พอ CI checkout โฟลเดอร์นั้นจะไม่มี
    ถ้า Dockerfile อ้างถึงมัน (เช่น public/ ของ Next.js) build จะพังเฉพาะบน CI
    ซึ่งหาสาเหตุยากกว่าพังในเครื่องมาก เพราะในเครื่องทุกอย่างดูปกติ
    """
    if TRACKED is None:
        return
    bucket = notes if optional else problems
    for child in sorted(context.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "node_modules":
            continue
        rel = child.relative_to(ROOT.parent).as_posix()
        if not any(f == rel or f.startswith(rel + "/") for f in TRACKED):
            bucket.append(f"{service}: โฟลเดอร์ {context.name}/{child.name}/ มีในเครื่อง "
                          f"แต่ git ไม่ได้เก็บไฟล์ไหนเลย -> หายไปตอน CI checkout "
                          f"(ใส่ .gitkeep ถ้าจำเป็นต้องมี)")


def main() -> int:
    raw = COMPOSE.read_text(encoding="utf-8")
    global TRACKED
    TRACKED = tracked_paths()
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        return sys.exit(f"YAML แตก: {e}")

    services: dict = doc.get("services") or {}
    print(f"บริการทั้งหมด {len(services)} ตัว\n")

    ports: dict[str, str] = {}
    for name, spec in services.items():
        spec = spec or {}
        profiles = spec.get("profiles") or []
        tag = f"  [profile: {','.join(profiles)}]" if profiles else ""

        build = spec.get("build")
        if build:
            if isinstance(build, str):
                context, dfname = ROOT / build, "Dockerfile"
            else:
                context = ROOT / build.get("context", ".")
                dfname = build.get("dockerfile", "Dockerfile")
            dockerfile = context / dfname
            if not context.exists():
                problems.append(f"{name}: ไม่มีโฟลเดอร์ {build}")
            elif not dockerfile.exists():
                problems.append(f"{name}: ไม่มี {dfname} ใน {context.name}/")
            else:
                check_dockerfile_copies(name, context, dockerfile, optional=bool(profiles))
                check_untracked_dirs(name, context, optional=bool(profiles))
            print(f"  {name:16} build {context.name}/{dfname}{tag}")
        else:
            print(f"  {name:16} image {spec.get('image', '?')}{tag}")

        for mapping in spec.get("ports") or []:
            host = str(mapping).split(":")[0].strip('"')
            if host in ports and not profiles:
                problems.append(f"พอร์ต {host} ถูกใช้ทั้ง {ports[host]} และ {name}")
            ports.setdefault(host, name)

        dep = spec.get("depends_on") or {}
        items = dep.items() if isinstance(dep, dict) else [(d, {}) for d in dep]
        for target, cond in items:
            if target not in services:
                problems.append(f"{name}: depends_on {target} ซึ่งไม่มีในไฟล์นี้")
                continue
            wants_healthy = isinstance(cond, dict) and cond.get("condition") == "service_healthy"
            target_spec = services.get(target) or {}
            if wants_healthy and "healthcheck" not in target_spec:
                # compose จะรอ healthcheck จาก image ถ้าไม่มีใน compose
                df = target_spec.get("build")
                ctx = ROOT / (df if isinstance(df, str) else (df or {}).get("context", "."))
                dfn = "Dockerfile" if isinstance(df, str) else (df or {}).get("dockerfile", "Dockerfile")
                in_image = (ctx / dfn).exists() and "HEALTHCHECK" in (ctx / dfn).read_text(encoding="utf-8")
                if not in_image:
                    problems.append(
                        f"{name}: รอ {target} ให้ healthy แต่ {target} ไม่มี healthcheck "
                        f"ทั้งใน compose และใน Dockerfile -> compose จะค้างรอตลอดไป")

    used = set(re.findall(r"\$\{([A-Z_][A-Z0-9_]*)", raw))
    declared = set()
    if ENV_EXAMPLE.exists():
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                declared.add(line.split("=", 1)[0].strip())
    for var in sorted(used - declared):
        # ตัวที่มีค่าตั้งต้นในไฟล์ (${X:-ค่า}) ไม่ตั้งก็ยังรันได้ แค่เตือนไว้
        has_default = re.search(r"\$\{" + var + r":-", raw)
        (notes if has_default else problems).append(
            f"ตัวแปร {var} ไม่มีใน .env.example" + (" (มีค่าตั้งต้น)" if has_default else ""))

    print()
    for n in notes:
        print(f"  หมายเหตุ: {n}")
    if problems:
        print(f"\nพบปัญหา {len(problems)} ข้อ")
        for p in problems:
            print(f"  ! {p}")
        return 1
    print("\nผ่านทุกข้อ — docker compose up ไม่ควรพังตั้งแต่ build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
