# CLAUDE.md — 02_api_backend

บริบทถาวรสำหรับ Claude Code เมื่อทำงานในโมดูล `02_api_backend` — อ่านทุกครั้งก่อนเริ่มงาน

## โปรเจกต์
RMUTT Study Planner — ระบบวางแผนการเรียนและตรวจตารางชนสำหรับนักศึกษา มทร.ธัญบุรี
02 คือ **API Gateway**: ทางเข้าเดียวของหน้าเว็บ (01)

## Source of truth
1. `02_api_backend/PLAN.md` (v2) — **ยึดไฟล์นี้ก่อนเสมอ**
2. `02_api_backend/03_process.txt`, `00_docs/05_data_model.md`, `00_docs/03_flow.md`
3. `06_schedule_conflict_engine/03_process.txt` (response ของ 06), `03_ai_router_agent/03_process.txt`

เอกสารขัดกัน → ยึด PLAN.md และแจ้งในสรุป · PLAN.md ไม่ได้ระบุ → **หยุดถาม อย่าเดา**

## หลักการทำงาน
- **Contract-first:** schema และ fixture มาก่อนโค้ด ทุก response ต้องตรง schema
- **Vertical slice:** ทำทีละ flow ให้ 01 เรียกได้จริงทุกวัน
- **02 ไม่มีตรรกะคำนวณเอง:** ชน/ไม่ชน/prereq/หน่วยกิตมาจาก 06, คำตอบ AI มาจาก 03/07

## Tech stack
Python 3.11 · FastAPI · Pydantic v2 · pydantic-settings · SQLAlchemy 2.x async (`postgresql+psycopg`) · Alembic ·
`redis.asyncio` · httpx · python-jose · structlog · ruff
Test: pytest, pytest-asyncio, httpx `AsyncClient`, fakeredis, **Postgres** สำหรับ API test

## โครงโฟลเดอร์ (ตาม PLAN.md 3.1)
```
02_api_backend/
├── src/               # คงชื่อเดิม: Dockerfile รัน src.main:app และ CI ตรวจ syntax จาก 0*/src
│   ├── api/v1/        # routers: auth, courses, students, plans, chat, feedback
│   ├── schemas/       # Pydantic = สัญญากลาง
│   ├── services/      # ประกอบ flow
│   ├── adapters/      # interface + mock / inprocess / http ของ 03–08
│   ├── repositories/  # DB เท่านั้น
│   ├── models/        # SQLAlchemy
│   ├── core/          # config, security, envelope, errors, middleware, masking
│   └── main.py
├── fixtures/          # JSON success/error/SSE ใช้ร่วมกับ 01
├── migrations/        # Alembic
├── scripts/seed_demo.py
├── tests/{unit,api,contract,sse}/
├── .env.example
├── handoff/           # ข้อเสนอแก้ไฟล์นอกโมดูล (compose, CI, 00_docs) ให้ทีมเอาไปใช้เอง
├── 01_env.txt  02_step.txt  03_process.txt   # เอกสารเดิมของโมดูล อัปเดตให้ตรงโค้ด
├── Dockerfile         # CMD uvicorn src.main:app (คงเดิม)
└── requirements.txt
```

## กติกาบังคับ
1. **Layer:** router → service → repository/adapter → model · router ห้ามแตะ DB · service ห้าม import fastapi
2. **Envelope** ทุก endpoint (ยกเว้น `/health` `/ready` `/metrics` และ `/chat` SSE)
   ```json
   { "ok": true,  "data": {}, "meta": { "request_id": "req_...", "took_ms": 0 } }
   { "ok": false, "error": { "code": "...", "message": "...", "details": {} }, "meta": { "request_id": "req_...", "took_ms": 0 } }
   ```
   HTTP status ตรงกับ code เสมอ · ทุก response มี header `X-Request-ID`
3. **Error code:** `AUTH_401` `FORBIDDEN_403` `NOT_FOUND_404` `CONFLICT_409` `PAYLOAD_413` `VALIDATION_422` `RATE_429` `UPSTREAM_502` (+ `INTERNAL_500` สำหรับ exception ที่ไม่คาดคิด ห้ามหลุด stack trace)
4. **Prefix** `/api/v1` ยกเว้น `/health` `/ready` `/metrics`
5. **รูปแบบข้อมูล:** เวลา `"day":"MON","start":"09:00","end":"11:50"` · ID เป็น integer ยกเว้น `section_id` เป็น string ·
   list ใช้ `{ "items": [], "next_cursor": "..." | null }`
6. **Auth:** บัญชีเดโมจาก env (`DEMO_USERNAME` / `DEMO_PASSWORD`) เทียบด้วย `hmac.compare_digest` · JWT ใน cookie `session`
   (HttpOnly, SameSite=Lax, Path=/, Secure เมื่อ HTTPS) · ทุก query ใต้ `/students/me` `/plans` `/chat` กรองด้วย `student_id` ของ session
7. **Adapter:** เรียกโมดูลอื่นผ่าน interface เท่านั้น เลือกด้วย `ADAPTER_04..08` = `mock|inprocess|http` · 03 ใช้ http เสมอ (`ROUTER_URL`)
8. **Timeout/retry** ตามตาราง PLAN.md 3.3 · ปลายทางล่ม/เกินเวลา → `UPSTREAM_502`
9. **PDPA:** ห้าม log/ส่งชื่อหรือรหัสนักศึกษาจริง · ใช้ `masking.hash_student_id()` และ `masking.scrub_text()` ก่อนส่ง 03 และก่อน log ·
   ห้าม log เนื้อไฟล์ import หรือเนื้อข้อความแชต · ไม่เก็บไฟล์ import หลัง parse
10. **Secrets:** อ่านจาก env เท่านั้น · สร้าง `.env.example` ได้ แต่ห้ามสร้าง/commit `.env`
11. **ข้อมูลตัวอย่าง** เป็นข้อมูลสังเคราะห์เท่านั้น · CI บล็อกรหัสรูปแบบ `1xxxxxxxxxxx-x` นอก `*/tests/fixtures/*`
12. **ขอบเขต: แก้/สร้างไฟล์เฉพาะใน `02_api_backend/` เท่านั้น ไม่มีข้อยกเว้น**
    ห้ามแก้ `docker-compose.yml`, `.env.example` ที่ root, `.github/`, `00_docs/`, `infra/` และโมดูลอื่น
    ถ้าจำเป็นต้องเปลี่ยนไฟล์เหล่านั้น → เขียนเป็นข้อเสนอพร้อม snippet ใน `02_api_backend/handoff/` แทน
    อ่านไฟล์ของโมดูลอื่นได้ (อ่านอย่างเดียว)

## การรัน test
```bash
docker compose up -d postgres redis                      # จาก root ของ ProJ-RMUTT-Planner
export TEST_DATABASE_URL=postgresql+psycopg://rmutt:change_me_please@localhost:5432/rmutt_test
cd 02_api_backend && pytest -q                            # unit test รันได้แม้ไม่มี Postgres (skip api/contract/sse)
ruff check .
```

## ก่อนจบทุกงาน
- `pytest -q` และ `ruff check .` ผ่าน
- ติ๊ก checkbox ที่เสร็จใน PLAN.md หัวข้อ 8
- อัปเดต `fixtures/` ถ้า response เปลี่ยน
- commit `[02] <สิ่งที่ทำ>` (ห้าม push)
- สรุป: ทำอะไร · สมมติฐานที่ใช้ · สิ่งที่ต้องให้ทีมตัดสิน · 01 เรียกอะไรได้แล้วบ้าง
