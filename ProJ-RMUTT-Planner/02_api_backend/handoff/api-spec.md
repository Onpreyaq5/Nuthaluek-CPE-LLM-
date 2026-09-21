# API Spec — 02_api_backend (สรุปจาก OpenAPI จริง)

สร้างจาก `app.openapi()` จริงหลัง Prompt 10 — ดูสคีมาละเอียดทุก field ที่ `handoff/openapi.json`
(นำเข้า Swagger UI / Postman ได้ตรง) หรือรันเซิร์ฟเวอร์แล้วเปิด `/docs` (Swagger) / `/redoc`

อัปเดตไฟล์นี้เมื่อ endpoint เปลี่ยน: `python -c "import json; from src.main import app; json.dump(app.openapi(), open('handoff/openapi.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)"`

## Base URL และ prefix
ทุก endpoint อยู่ใต้ `/api/v1` ยกเว้น `GET /health`, `GET /ready`, `GET /metrics` (ไม่มี prefix, ไม่มี envelope)

## Auth
- `POST /api/v1/auth/login` `{username, password}` → ตั้ง cookie `session` (HttpOnly, SameSite=Lax, JWT)
  ไม่มี token ใน response body
- ทุก request ที่ต้อง login ส่ง cookie นี้ไปด้วย (`credentials: include` ฝั่ง frontend)
- `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`

## Response envelope
```json
{ "ok": true,  "data": {}, "meta": { "request_id": "req_...", "took_ms": 12 } }
{ "ok": false, "error": { "code": "VALIDATION_422", "message": "...", "details": {} }, "meta": {...} }
```
ยกเว้น `POST /api/v1/chat` (SSE, `Content-Type: text/event-stream`, ไม่มี envelope ต่อ event)
ทุก response มี header `X-Request-ID` เอาไว้ตามหา log

## Error codes
`AUTH_401` ไม่ได้ login/token หมดอายุ · `FORBIDDEN_403` login แล้วแต่ไม่ใช่เจ้าของ resource ·
`NOT_FOUND_404` · `CONFLICT_409` (เช่นชื่อแผนซ้ำ) · `PAYLOAD_413` (ไฟล์ import ใหญ่เกิน) ·
`VALIDATION_422` · `RATE_429` (มี header `Retry-After`) · `UPSTREAM_502` (โมดูล 03-08 ล่ม/timeout,
`details.module` บอกว่าเป็นโมดูลไหน) · `INTERNAL_500`

## Endpoints

| Method | Path | ต้อง login | เรียกโมดูล | หมายเหตุ |
|---|---|---|---|---|
| POST | `/auth/login` | - | - | rate limit 5/min ต่อ IP |
| GET | `/auth/me` | ✅ | - | |
| POST | `/auth/logout` | - | - | เคลียร์ cookie เสมอแม้ไม่ได้ login |
| GET | `/courses` | ✅ | 04 | cache redis, cursor pagination `{items, next_cursor}` |
| GET | `/courses/{code}/sections` | ✅ | 04 | cache redis |
| GET | `/students/me/profile` | ✅ | 05 | |
| GET | `/students/me/transcript` | ✅ | 05 | |
| POST | `/students/me/import` | ✅ | 05 | multipart HTML transcript, ไม่เก็บไฟล์ดิบหลัง parse |
| POST | `/plans/validate` | ✅ | 04, 06 | ไม่บันทึกแผน แค่เช็ค |
| POST | `/plans/auto` | ✅ | 04, 06, 07 | 07 ล่ม → `explanation: null` + warning ไม่ fail ทั้งคำขอ |
| POST | `/plans` | ✅ | - | บันทึกแผน ชื่อซ้ำ (ต่อ student+term) → 409 |
| GET | `/plans` | ✅ | - | cursor pagination, เฉพาะของตัวเอง |
| GET | `/plans/{plan_id}` | ✅ | - | ไม่ใช่เจ้าของ → 403, ไม่มีจริง → 404 |
| DELETE | `/plans/{plan_id}` | ✅ | - | เหมือนข้างบน |
| GET | `/plans/{plan_id}/explain` | ✅ | 07 | |
| POST | `/chat` | ✅ | 03 (http เสมอ) | SSE, rate limit 10/min ต่อ student |
| GET | `/chat/sessions` | ✅ | - | cursor pagination, เฉพาะของตัวเอง |
| GET | `/chat/sessions/{session_id}/messages` | ✅ | - | ไม่ใช่เจ้าของ session → 403 |
| POST | `/feedback` | ✅ | 08 (async ผ่าน log_queue) | target เป็น plan หรือ chat message ของตัวเองเท่านั้น |

## Adapter modes (04-08)
ตั้งผ่าน env `ADAPTER_04`..`ADAPTER_08` = `mock` (ข้อมูลสังเคราะห์ในโค้ด, ใช้ตอนยังไม่มีโมดูลจริง) |
`inprocess` (import โมดูลข้างเคียงตรง ๆ ผ่าน `MODULE_0X_DIR`, เฉพาะ 04/05 ที่มี implementation) |
`http` (เรียกผ่าน `*_URL`, ต้องมีโมดูลนั้นรันจริงและมี `GET /health`)
โมดูล 03 (chat router) ใช้ `http` เสมอไม่มีโหมดอื่น (`ROUTER_URL`)

**สถานะปัจจุบัน (ดู PROGRESS.md ล่าสุด):** 04/05 ยังไม่มีโค้ดจริงจากทีมโมดูลนั้น (`inprocess`/`http` ยัง
ทดสอบไม่ได้กับของจริง) — ใช้ `mock` เป็นค่าเริ่มต้นจนกว่าจะมีสัญญาจริง 03 ยังไม่มี router จริงให้ต่อเช่นกัน

## Timeouts / retry (ตาราง PLAN.md 3.3)
อ่าน (`courses`, `students/me/*`) 5s, retry 1 · validate 5s, retry 1 · auto 15s, retry 0 ·
เขียน (`plans` POST/DELETE, `feedback`) 10s, retry 0 · chat: start 15s, idle 30s, total 120s
ปลายทางล่ม/เกินเวลา → `UPSTREAM_502` เสมอ ไม่ throw exception ดิบออกไป

## Fixtures
`fixtures/**/*.json` (success/error ต่อ endpoint) และ `fixtures/sse/*.txt` (ลำดับ event SSE ครบทุกเคส
รวม error/cancel) — capture จาก response จริงทุกครั้งที่ endpoint เปลี่ยน (ไม่ใช่เขียนมือ), ตรวจอัตโนมัติ
ด้วย `tests/contract/test_fixtures_match_schema.py`

## /health, /ready, /metrics
- `GET /health` → `{"status": "ok"}` เสมอถ้า process ยังอยู่ (ไม่เช็ค dependency)
- `GET /ready` → `{"ready": bool, "checks": {"postgres": bool, "redis": bool, "03": bool, "04": bool?, ...}}`
  (04-08 เช็คเฉพาะตัวที่ตั้ง `ADAPTER_xx=http`) ไม่ ready → HTTP 503
- `GET /metrics` → Prometheus text (`prometheus-fastapi-instrumentator` + `log_dropped_total` gauge)
