# 02_api_backend — RMUTT Study Planner API Gateway

ทางเข้าเดียว (API Gateway) ของหน้าเว็บ (โมดูล 01) สำหรับระบบวางแผนการเรียนและตรวจตารางชน
มทร.ธัญบุรี ไม่มีตรรกะคำนวณเอง — ชน/prereq/หน่วยกิตมาจาก 06, คำตอบ AI มาจาก 03/07

โครงสร้าง, กติกาบังคับ, source of truth: ดู [`CLAUDE.md`](./CLAUDE.md) และ [`PLAN.md`](./PLAN.md)
สถานะความคืบหน้าล่าสุดของแต่ละ prompt: ดู [`PROGRESS.md`](./PROGRESS.md)
สรุป endpoint ทั้งหมด + ตาราง adapter: ดู [`handoff/api-spec.md`](./handoff/api-spec.md) และ
[`handoff/openapi.json`](./handoff/openapi.json)

## รันแบบ dev (ไม่มี Docker)

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # แก้ค่าตามเครื่องตัวเอง ห้าม commit .env

# ต้องมี Postgres + Redis จริง (ปรับ DATABASE_URL/REDIS_URL ใน .env ให้ตรง)
alembic upgrade head
python -m scripts.seed_demo        # สร้างบัญชีเดโมตาม DEMO_* ใน .env

python -m uvicorn src.main:app --reload   # Linux/Mac
python scripts/run_dev.py                 # Windows (ProactorEventLoop เริ่มก่อน uvicorn ทำให้ psycopg async พัง)
```

เปิด `http://localhost:8000/docs` (Swagger) หรือ `/redoc` เพื่อดู API แบบ interactive

## รันด้วย Docker

```bash
docker build -t rmutt-api .
docker run -p 8000:8000 --env-file .env \
  -e DATABASE_URL=postgresql+psycopg://rmutt:change_me_please@<postgres-host>:5432/rmutt \
  -e REDIS_URL=redis://<redis-host>:6379/0 \
  rmutt-api
```
`entrypoint.sh` รัน `alembic upgrade head` อัตโนมัติก่อน uvicorn เสมอ; ตั้ง `SEED_DEMO=true` เพื่อสร้าง
บัญชีเดโมตอน container start (เฉพาะ dev/demo เท่านั้น — ห้ามใช้ production จริง)

ยังไม่มี `docker-compose.yml` ที่ root ของ repo (ดูข้อเสนอที่ [`handoff/compose.md`](./handoff/compose.md))
— รัน Postgres/Redis เองด้วย `docker run` หรือดู `scripts/smoke.sh` เป็นตัวอย่างเต็มรูปแบบ

## Env vars หลัก

| ตัวแปร | ความหมาย |
|---|---|
| `DATABASE_URL` / `REDIS_URL` | connection string ของ Postgres / Redis |
| `JWT_SECRET`, `JWT_EXPIRE_MINUTES` | เซ็น/ตรวจ JWT ใน cookie `session` |
| `DEMO_USERNAME`, `DEMO_PASSWORD`, `DEMO_STUDENT_ID` | บัญชีเดโมสำหรับ 01 ใช้ทดสอบ |
| `CORS_ORIGINS` | origin ของหน้าเว็บ (comma-separated) |
| `ADAPTER_04`..`ADAPTER_08` | `mock` \| `inprocess` \| `http` ต่อโมดูล — 03 ใช้ `http` เสมอ |
| `ROUTER_URL`, `COURSE_CATALOG_URL`, `STUDENT_DATA_URL`, `PLAN_ENGINE_URL`, `EXPLAINER_URL`, `LOG_SINK_URL` | URL ของโมดูล 03-08 เมื่อ adapter เป็น `http` |
| `TIMEOUT_*_SECONDS`, `RETRY_*` | timeout/retry ต่อประเภทคำขอ (PLAN.md ตาราง 3.3) |

รายการเต็ม: [`.env.example`](./.env.example) · รายละเอียดแพ็กเกจ/runtime: [`01_env.txt`](./01_env.txt)

**สถานะ adapter ปัจจุบัน:** โมดูล 04/05 ยังไม่มีโค้ดจริงจากทีมเจ้าของ และยังไม่มี router (03) จริงให้ต่อ
— ใช้ `mock` เป็นค่าเริ่มต้นทุกตัวจนกว่าจะมีสัญญาจริง (ดู PROGRESS.md สำหรับรายละเอียด)

## ตัวอย่าง curl (flow หลักที่ 01 ใช้)

```bash
# 1) login — ได้ cookie session กลับมา
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}'

# 2) ดูรายวิชา
curl -b cookies.txt http://localhost:8000/api/v1/courses

# 3) ตรวจตารางชนก่อนบันทึก
curl -b cookies.txt -X POST http://localhost:8000/api/v1/plans/validate \
  -H "Content-Type: application/json" \
  -d '{"term":"1/2569","section_ids":["CPE201-01"]}'

# 4) บันทึกแผน
curl -b cookies.txt -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" \
  -d '{"term":"1/2569","name":"แผนหลัก","section_ids":["CPE201-01"]}'

# 5) แชต (SSE) — ต้องมี router (03) จริงตอบสนอง ไม่งั้นได้ UPSTREAM_502
curl -b cookies.txt -N -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":null,"message":"ลงทะเบียนตอนไหน"}'
```

รายการ endpoint ทั้งหมด + ตัวอย่าง request/response แต่ละตัว: [`handoff/api-spec.md`](./handoff/api-spec.md)

## Test

```bash
# unit test อย่างเดียว (ไม่ต้องมี Postgres) — tests/api, tests/sse จะถูก skip อัตโนมัติ
pytest -q

# ครบทุกกลุ่มรวม api/contract/sse (ต้องมี Postgres จริง)
export TEST_DATABASE_URL=postgresql+psycopg://rmutt:change_me_please@localhost:5432/rmutt_test
pytest -q
ruff check .

# หรือให้ script จัดการ Postgres ชั่วคราวให้เอง (ต้องมี Docker)
sh scripts/test.sh

# smoke test แบบ clean-clone จริง: build image, รัน Postgres+Redis+api จริง, curl ครบ flow
sh scripts/smoke.sh
```
Redis ไม่ต้องมีจริงตอนรัน `pytest` — ทุก test ต่อ `fakeredis` แทนโดยอัตโนมัติ (`tests/conftest.py`)

## โครงสร้างโค้ด

```
src/
├── api/v1/        # router: auth, courses, students, plans, chat, feedback (FastAPI เท่านั้น)
├── schemas/       # Pydantic = สัญญากลางกับ 01
├── services/      # ประกอบ flow, orchestrate adapter/repository (ห้าม import fastapi)
├── adapters/      # interface (Protocol) + mock/inprocess/http ของโมดูล 03-08
├── repositories/  # DB query เท่านั้น (SQLAlchemy)
├── models/        # SQLAlchemy ORM
├── core/          # config, security, envelope, errors, middleware, masking, rate_limit, cache
└── main.py        # FastAPI app, lifespan, exception handler, /health /ready /metrics
```
Layer บังคับ: router → service → repository/adapter → model (router ห้ามแตะ DB, service ห้าม import fastapi)

## ข้อจำกัดที่ทีมต้องรู้

- โมดูล 04/05/06/07/08/03 ยังไม่มีโค้ด/endpoint จริงให้ต่อ — ทุกอย่างทดสอบผ่าน `mock` adapter
  (ข้อมูลสังเคราะห์) เท่านั้น ยังไม่เคยเทสกับของจริง
- `handoff/` มีข้อเสนอไฟล์นอกโมดูล (compose.yml, CI) ที่ทีมต้องเอาไปรวมเอง — 02 ไม่แก้ไฟล์นอก
  `02_api_backend/` ตามกติกาใน CLAUDE.md
- คำถามที่ยังไม่มีคำตอบจากทีม: ดู PLAN.md หัวข้อ 12
