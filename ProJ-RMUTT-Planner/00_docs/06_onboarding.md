# 06 — เริ่มงานวันแรก (Onboarding)

สำหรับคนที่เพิ่งเข้าทีม — ทำตามนี้ 30 นาที แล้วจะพร้อมเขียนโค้ด

---

## ขั้นที่ 1 — เตรียมเครื่อง (10 นาที)

ต้องมี: Git, Docker Desktop, Python 3.11+, Node 20+ (เฉพาะคนทำ `01_web_app`)

```bash
git clone https://github.com/Onpreyaq5/Nuthaluek-CPE-LLM-.git
cd Nuthaluek-CPE-LLM-/ProJ-RMUTT-Planner
cp .env.example .env
```

Windows เจอ `Filename too long` → `git config --global core.longpaths true`

## ขั้นที่ 2 — อ่านเอกสาร 3 ไฟล์ (10 นาที)

| อ่านอะไร | ได้อะไร |
|---|---|
| [`01_architecture.md`](01_architecture.md) | ภาพรวมว่าโมดูลไหนคุยกับใคร ผ่านพอร์ตอะไร |
| [`03_flow.md`](03_flow.md) | ระบบทำงานยังไงตั้งแต่ผู้ใช้กดจนได้คำตอบ (FLOW A-F) |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | กติกา branch / PR / ข้อห้าม |

แล้วเปิดโฟลเดอร์โมดูลของตัวเอง อ่าน `01_env.txt` → `02_step.txt` → `03_process.txt` ตามลำดับ

## ขั้นที่ 3 — รันของที่มีอยู่ให้ผ่าน (10 นาที)

```bash
# ทดสอบ parser ที่เขียนไว้แล้ว — ต้องผ่านหมด
cd 04_course_data_services && pip install -r requirements.txt pytest && pytest -q && cd ..
cd 05_data_integration     && pip install -r requirements.txt pytest && pytest -q && cd ..

# ลองรัน service ของตัวเอง
docker compose up -d --build <ชื่อ service>
curl http://localhost:<port>/health
```

ถ้าผ่านหมด = เครื่องพร้อม

## ขั้นที่ 4 — งานชิ้นแรก

1. ไปที่ [Issues](https://github.com/Onpreyaq5/Nuthaluek-CPE-LLM-/issues) เลือกอันที่ติด label โมดูลของคุณ
   (ยังไม่มี issue → เปิดเองจาก `02_step.txt` ของโมดูล ทีละ STEP)
2. เติมชื่อตัวเองใน [`04_team_roles.md`](04_team_roles.md)
3. แตก branch → เขียน → PR

```bash
git checkout main && git pull
git checkout -b feat/<โมดูลของคุณ>
# เขียนโค้ด + เขียน test
git add <โฟลเดอร์ของคุณ>/
git commit -m "[0X] ทำอะไร"
git push -u origin feat/<โมดูลของคุณ>
```

เปิด PR บน GitHub → รอ CI เขียว → ให้เพื่อน review → Squash and merge

---

## สิ่งที่ CI จะเช็คให้อัตโนมัติทุก PR

| Check | ถ้าแดงแปลว่า |
|---|---|
| `pytest 04_course_data_services` | test ของโมดูล 04 พัง |
| `pytest 05_data_integration` | test ของโมดูล 05 พัง |
| `syntax check (all services)` | มี Python syntax error |
| `docker compose config` | แก้ `docker-compose.yml` แล้วผิดรูปแบบ |
| `no secrets or student data` | มี `.env` / API key / รหัสนักศึกษาจริง หลุดเข้า commit |

**merge ไม่ได้จนกว่าจะเขียวครบ** — ถ้าแดงให้กดเข้าไปอ่าน log ก่อนถามเพื่อน

เมื่อโมดูลของคุณมี `tests/` แล้ว อย่าลืมเพิ่มชื่อโฟลเดอร์ลงใน `matrix.service`
ที่ [`.github/workflows/ci.yml`](https://github.com/Onpreyaq5/Nuthaluek-CPE-LLM-/blob/main/.github/workflows/ci.yml) ด้วย

---

## คำถามที่ทีมยังต้องหาคำตอบ

ใครไปเจอคำตอบให้มาอัปเดตที่นี่ + แจ้งในกลุ่ม

- [ ] เพดานหน่วยกิต **เทอมฤดูร้อน** เท่าไหร่ (ตอนนี้ตั้ง `SUMMER_MAX_CREDITS=9` ไว้ชั่วคราว)
- [ ] ขั้นต่ำต่อเทอมเท่าไหร่ (ตอนนี้ตั้ง 9)
- [ ] รหัสวิชาเดียวกันคนละปีหลักสูตร (`04000202-63` vs `04000202-68`) ลงแทนกันได้ไหม
- [ ] ขอไฟล์รายวิชา/ตารางสอนจาก สวท. ได้ไหม หรือต้องให้นักศึกษาเซฟ HTML เอง
- [ ] เอกสารระเบียบ/คู่มือนักศึกษา ฉบับ PDF เอามาจากไหน (ใช้ทำ RAG ใน `07`)
