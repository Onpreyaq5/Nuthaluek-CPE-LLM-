# 02_api_backend — แผนงาน (Work Plan) ฉบับปรับปรุง

> โมดูล: `02_api_backend` · branch: `feat/api-backend` · พอร์ต: `8000`
> สถานะ: **ร่าง v2 รอทีมรีวิว** — ปรับตามข้อเสนอของ `01_web_app_work_plan.md`
> หลักการ: **ทำสัญญาก่อนโค้ด (contract-first)** และ **ส่งงานทีละ flow (vertical slice)** ให้ 01 เชื่อมได้ทุกวัน

---

## 1. บทบาทของ 02 ในระบบ

02 คือ **API Gateway** — ประตูทางเดียวที่หน้าเว็บ (01) คุยด้วย

- รับ request จากหน้าเว็บ (JSON หรือไฟล์ multipart) และตรวจ session
- ดึง/บันทึกข้อมูลผู้ใช้ในฐานข้อมูล (โปรไฟล์ ความชอบ แผน ประวัติแชต)
- เรียกโมดูลที่เป็นเจ้าของตรรกะ แล้วห่อผลเป็นรูปแบบเดียวกันส่งกลับ
- เก็บ log ส่งให้ 08 แบบไม่บล็อกผู้ใช้

**02 ไม่คำนวณอะไรเอง** — เรื่องชน/ไม่ชน/หน่วยกิตมาจาก 06 เท่านั้น, คำตอบ AI มาจาก 03/07

### เส้นทางของ request

| แบบ | ตัวอย่าง | ไปที่ไหน |
|---|---|---|
| ไม่ผ่าน Router 03 | `/plans/validate`, `/plans/auto`, `/courses`, `/students/me/*` | 04 / 05 / 06 / 07 ตรง (`/plans/auto` และ `/plans/{id}/explain` อาจใช้ LLM ที่ 07) |
| ผ่าน Router 03 | `/chat` | สร้าง enriched JSON → 03 → กรองแล้ว stream กลับ |

---

## 2. การตัดสินใจหลัก

| เรื่อง | ข้อตกลง | สถานะ |
|---|---|---|
| กรอบเวลา | 7 วัน (D1–D7) ตามแผน 01 | รอยืนยันวันเริ่ม/วันส่ง |
| วิธีล็อกอิน | บัญชีเดโมเดียว `admin` / `admin1234` ออก JWT ใน httpOnly cookie (รายละเอียดหัวข้อ 5) | ✅ ตกลงแล้ว |
| prefix | ทุก endpoint ขึ้นต้น `/api/v1` ยกเว้น `/health` `/ready` `/metrics` | ✅ 01 ยืนยันแล้ว |
| endpoint อัปโหลด | `POST /api/v1/students/me/import` (ไฟล์ HTML) | ✅ 01 ยืนยันแล้ว |
| ฐานข้อมูล | Postgres ทั้ง dev และ CI; SQLite ใช้ได้เฉพาะ unit test ที่ไม่แตะ migration | ✅ |
| วิธีเรียกโมดูล 04–07 | ผ่าน interface กลาง เลือก `inprocess` / `http` / `mock` ด้วย env (หัวข้อ 3) | ⚠️ ทีมเลือกค่าเริ่มต้น |
| Deploy | ขึ้นกับข้อบน: in-process → app container เดียว + Postgres/Redis; http → หลาย services ผ่าน Compose | ⚠️ รอ 02/08 |

---

## 3. สถาปัตยกรรมภายใน

### 3.1 โครงโฟลเดอร์

```text
02_api_backend/
├── src/               # คงชื่อเดิมให้ตรง Dockerfile และ CI
│   ├── api/v1/            # routers: auth, courses, students, plans, chat, feedback
│   ├── schemas/           # Pydantic — สัญญากลาง (แหล่งความจริงของ OpenAPI)
│   ├── services/          # ประกอบ flow, ไม่มีตรรกะคำนวณเอง
│   ├── adapters/          # interface + inprocess / http / mock ของ 03–08
│   ├── repositories/      # เข้าถึง DB
│   ├── models/            # SQLAlchemy
│   ├── core/              # config, security, envelope, errors, middleware, masking
│   └── main.py
├── fixtures/              # JSON ตัวอย่าง success/error/SSE — ใช้ร่วมกับ 01
├── migrations/            # Alembic
├── tests/
├── .env.example
└── Dockerfile
```

### 3.2 Adapter แทนการผูกกับ HTTP ตายตัว

02 เรียกทุกโมดูลผ่าน interface เช่น

```python
class PlanValidator(Protocol):
    async def validate(self, term: str, section_ids: list[str], student: StudentContext) -> ValidationResult: ...
```

แต่ละ interface มี 3 implementation เลือกด้วย env รายโมดูล

| ค่า | ความหมาย | ใช้เมื่อ |
|---|---|---|
| `mock` | อ่านจาก `fixtures/` (mock 06 ตรวจเวลาชนแบบง่ายได้จริง) | โมดูลปลายทางยังไม่พร้อม |
| `inprocess` | import แพ็กเกจ Python ของโมดูลนั้นมาเรียกตรง | 04/05/06 เป็นตรรกะล้วนและทีมเลือก container เดียว |
| `http` | เรียกผ่าน httpx ตาม URL ใน compose | โมดูลรันเป็น service แยก (03 ใช้แบบนี้เสมอ) |

```env
ADAPTER_04=mock        # mock | inprocess | http
ADAPTER_05=mock
ADAPTER_06=mock
ADAPTER_07=mock
ADAPTER_08=mock
ROUTER_URL=http://router:8001
```

ข้อดี: 01 เริ่มเชื่อมได้ตั้งแต่ D1 ด้วย mock และเปลี่ยนเป็นของจริงทีละโมดูลโดยแก้แค่ env

### 3.3 นโยบาย timeout / retry

| ประเภทคำขอ | timeout | retry |
|---|---|---|
| อ่านข้อมูล (GET courses, sections, transcript) | 5 วินาที | 1 ครั้ง |
| ตรวจแผน `/plans/validate` | 5 วินาที | 1 ครั้ง (ไม่มีผลข้างเคียง) |
| สร้างแผนอัตโนมัติ `/plans/auto` | 15 วินาที (06 ใช้ได้ถึง 10 วินาที) | ไม่ retry |
| import / feedback / บันทึกแผน | 10 วินาที | ไม่ retry |
| แชต (03) | รอเริ่ม stream 15 วินาที, idle 30 วินาที, รวม 120 วินาที | ไม่ retry |

ถ้าปลายทางล่มหรือเกินเวลา → `UPSTREAM_502`

---

## 4. สัญญา API (Contract)

### 4.1 Envelope

ทุก response ห่อด้วย envelope เดียวกัน (ยกเว้น `/chat` ที่เป็น SSE และ `/health` `/ready` `/metrics`)

```json
{ "ok": true,  "data": { }, "meta": { "request_id": "req_8f2a", "took_ms": 42 } }
{ "ok": false, "error": { "code": "VALIDATION_422", "message": "...", "details": {} },
  "meta": { "request_id": "req_8f2a", "took_ms": 3 } }
```

- error มี `meta.request_id` ด้วย และทุก response มี header `X-Request-ID`
- HTTP status ตรงกับ code เสมอ (ไม่คืน 200 สำหรับ error)
- `/metrics` ใช้ Prometheus text format ไม่ห่อ JSON

### 4.2 Error code

| code | HTTP | เกิดเมื่อ |
|---|---|---|
| `AUTH_401` | 401 | ไม่ได้ล็อกอิน / session หมดอายุ / รหัสผ่านผิด |
| `FORBIDDEN_403` | 403 | พยายามเข้าถึงข้อมูลที่ไม่ใช่ของตัวเอง |
| `NOT_FOUND_404` | 404 | ไม่พบข้อมูล |
| `CONFLICT_409` | 409 | เช่น บันทึกแผนชื่อซ้ำ |
| `PAYLOAD_413` | 413 | ไฟล์ import ใหญ่เกินกำหนด |
| `VALIDATION_422` | 422 | ข้อมูลผิดรูปแบบ |
| `RATE_429` | 429 | เรียกถี่เกินกำหนด |
| `UPSTREAM_502` | 502 | โมดูลปลายทางล่มหรือช้าเกิน |

### 4.3 Endpoint ทั้งหมด

| Method | Path | Input หลัก | Output หลัก | เรียกไปที่ | Slice |
|---|---|---|---|---|---|
| POST | `/auth/login` | `username, password` | ข้อมูลผู้ใช้ + ตั้ง cookie | config / DB | 1 |
| GET | `/auth/me` | cookie | `username, student_id, role` | DB | 1 |
| POST | `/auth/logout` | cookie | ลบ cookie | — | 1 |
| GET | `/courses` | `q, term, day, teacher, page` | รายการวิชา | 04 | 2 |
| GET | `/courses/{code}/sections` | `term` | section + คาบเรียน + ที่นั่ง + สอบ | 04 | 2 |
| POST | `/plans/validate` ★ | `term, section_ids[]` | `conflicts[], warnings[], summary` | 05 → 06 | 3 |
| POST | `/plans` | `term, name, section_ids[]` | `plan_id` | DB | 3 |
| GET | `/plans` | `term` | รายการแผน (ชื่อ, หน่วยกิต, วันที่แก้ไข) | DB | 3 |
| GET | `/plans/{id}` 🆕 | — | แผนเต็ม: section + คาบเรียน + ผลตรวจล่าสุด | DB | 3 |
| DELETE | `/plans/{id}` 🆕 | — | ลบแผน | DB | 3 |
| POST | `/chat` | `session_id \| null, message, plan_draft` | SSE stream | 03 | 4 |
| GET | `/chat/sessions` 🆕 | `limit, cursor` | รายการ session ของผู้ใช้ (ใหม่สุดก่อน) | DB | 4 |
| GET | `/chat/sessions/{id}/messages` 🆕 | `limit, cursor` | ข้อความ + sources + status | DB | 4 |
| GET | `/students/me/profile` | — | หลักสูตร, ชั้นปี, GPAX, หน่วยกิต | DB / 05 | 5 |
| GET | `/students/me/transcript` | — | วิชา+เกรด, หน่วยกิตแต่ละหมวด | 05 | 5 |
| POST | `/students/me/import` | ไฟล์ HTML (multipart) | จำนวนวิชาที่นำเข้า, วิชาที่ต้องลงใหม่, คำเตือน | 05 | 5 |
| POST | `/plans/auto` ★ | `term, preferences, must_include` | แผน 3–5 แบบ + เงื่อนไขที่ผ่อน | 05 → 06 → 07 | 5 |
| GET | `/plans/{id}/explain` | — | คำอธิบาย + แหล่งอ้างอิง | 07 | 5 |
| POST | `/feedback` | `target_type, target_id, rating, reason` | `feedback_id` | DB → 08 | 5 |
| GET | `/health` `/ready` `/metrics` | — | สถานะระบบ | — | 0 / 6 |

🆕 = เพิ่มใหม่จาก v1 ตามที่ 01 ต้องการ

- ทุก path ข้างบน (ยกเว้น health/ready/metrics) อยู่ใต้ `/api/v1`
- รูปแบบเวลาที่ API ส่งออก: `"day": "MON", "start": "09:00", "end": "11:50"` (DB เก็บเป็นนาทีจากเที่ยงคืน 02 แปลงให้)
- ID ทุกตัวเป็น integer ยกเว้น `section_id` ที่เป็น string ตามข้อมูลของ 04
- list ใช้ cursor pagination: `data: { items: [], next_cursor: "..." | null }`

### 4.4 Import HTML

- form field ชื่อ `file`, ขนาดสูงสุด 2 MB (เสนอ), รับเฉพาะ `text/html`
- 02 ตรวจเนื้อหาไม่เชื่อแค่นามสกุล และไม่เก็บไฟล์ต้นฉบับหลัง parse เสร็จ
- ต้องมี `fixtures/import/sample_sanitized.html` + ผล parse ที่คาดหวัง ใช้ร่วมกับ 01 และ 05

---

## 5. การล็อกอิน (Demo Auth)

รอบนี้ใช้ **บัญชีเดโมเดียว** เพื่อให้ทดลองใช้งานได้ทันที

| รายการ | ค่า |
|---|---|
| username | `admin` |
| password | `admin1234` |
| ผูกกับ | โปรไฟล์นักศึกษาจำลอง `DEMO_STUDENT_ID` ที่ seed ไว้ใน DB |
| role | `student` (สิทธิ์เท่านักศึกษาทั่วไป ไม่มีหน้าจัดการระบบ) |

### Flow

1. หน้าเว็บส่ง `POST /api/v1/auth/login` พร้อม `{"username": "admin", "password": "admin1234"}`
2. 02 เทียบกับค่าใน env ด้วย `hmac.compare_digest`
3. ถ้าถูก ออก JWT (อายุ 8 ชั่วโมง) ใส่ cookie `session` แบบ `HttpOnly; SameSite=Lax; Path=/` (เพิ่ม `Secure` เมื่อรันบน HTTPS)
4. ถ้าผิด คืน `AUTH_401` ข้อความเดียวกันทุกกรณี ("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
5. `POST /auth/logout` ลบ cookie; 01 ได้ `AUTH_401` เมื่อไหร่ให้กลับหน้า login

### การตั้งค่า

```env
DEMO_USERNAME=admin
DEMO_PASSWORD=admin1234
DEMO_STUDENT_ID=6500000000
JWT_SECRET=change-me
JWT_EXPIRE_MINUTES=480
CORS_ORIGINS=http://localhost:5173
```

- อ่านค่าจาก env เท่านั้น ไม่ฝังในโค้ด; ค่าข้างบนอยู่ใน `.env.example` เพื่อให้ทีมรันได้ทันที
- โปรไฟล์ที่ผูกกับบัญชีนี้ต้องเป็น **ข้อมูลสังเคราะห์** ไม่ใช่ข้อมูลนักศึกษาจริง
- `/auth/login` นับรวมใน rate limit (5 ครั้ง/นาที ต่อ IP)
- CORS ระบุ origin ชัดเจน + `allow_credentials=True` ไม่ใช้ `*`
- ทุก endpoint ใต้ `/students/me`, `/plans`, `/chat` ผ่าน dependency `current_user` และกรองด้วย `student_id` ของ session เสมอ เพื่อให้ต่อยอดเป็นหลายบัญชีได้โดยไม่ต้องแก้ repository

> ถ้าต้องใช้ข้อมูลนักศึกษาจริงในอนาคต ต้องเปลี่ยนเป็นการยืนยันตัวตนจริง (เช่น SSO มหาวิทยาลัย) ก่อน — ไม่อยู่ในรอบนี้

---

## 6. สัญญากับ 03 (Router / AI)

### 6.1 Enriched JSON ที่ 02 ส่งให้ 03

```json
{
  "request_id": "req_8f2a",
  "session_id": 7,
  "query": "ช่วยวางแผนลงทะเบียนเทอมหน้า อยากว่างวันศุกร์",
  "role": "student",
  "student": {
    "id_hash": "a91c...e0",
    "program_id": "CPE-2566",
    "curriculum_year": 2566,
    "year_level": 3,
    "credits_earned": 80,
    "preferences": { "free_days": ["FRI"], "no_early_class": true, "max_credits": 21 }
  },
  "history": [
    { "role": "user", "content": "เทอมนี้ผมติด F ฟิสิกส์" },
    { "role": "assistant", "content": "รับทราบครับ ..." }
  ],
  "plan_draft": null,
  "term": "1/2569"
}
```

- ห้ามมีชื่อหรือรหัสนักศึกษาจริง; `id_hash` ใช้ HMAC ด้วย secret ของ 02
- `query` และ `history` ผ่านตัวกรองข้อความก่อนส่ง (ปิดรหัสนักศึกษา 10 หลัก, เบอร์โทร, อีเมล)
- `curriculum_year` ต้องมีเสมอ เพราะ RAG ใช้กรองระเบียบตามรุ่น
- `history` = 10 ข้อความล่าสุดที่ status = `complete`

### 6.2 SSE event ที่ 02 ส่งต่อให้หน้าเว็บ

Response: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`
ทุก event คั่นด้วยบรรทัดว่าง

```text
data: {"type":"session","session_id":7}

data: {"type":"tool_start","tool":"search_knowledge"}

data: {"type":"tool_end","tool":"search_knowledge"}

data: {"type":"token","text":"ถอนรายวิชาได้"}

data: {"type":"sources","items":[{"title":"ข้อบังคับฯ","section":"ข้อ 18","page":12,"document_id":"doc-regulation-2566","url":null}]}

data: {"type":"done","message_id":301}

```

| Event | ความหมาย | 02 ทำอะไร |
|---|---|---|
| `session` | session ที่ใช้/สร้างใหม่ | ส่งเป็น event แรกเสมอ (สร้าง session เองถ้า `session_id: null`) |
| `tool_start` / `tool_end` | Agent กำลังทำขั้นไหน | ส่งต่อเฉพาะชื่อ tool ใน allowlist, ตัด arguments ทิ้ง |
| `token` | ข้อความคำตอบทีละส่วน | ส่งต่อ + สะสมไว้บันทึก |
| `sources` | แหล่งอ้างอิง (แทนที่ชุดเดิมทั้งชุด) | ตรวจ schema แล้วส่งต่อ |
| `done` | จบสมบูรณ์ | บันทึกข้อความ status `complete` |
| `error` 🆕 | ผิดพลาดระหว่าง stream | `{"type":"error","code":"UPSTREAM_502","message":"..."}` แล้วปิด stream |

- event ที่ไม่อยู่ในตารางนี้ **ไม่ส่งต่อ**
- ถ้าผิดพลาดก่อนเริ่ม stream → คืน HTTP error ปกติตาม envelope
- ถ้า 03 ปิด stream โดยไม่มี `done` → 02 ส่ง `error` และบันทึกเป็น `interrupted`
- ถ้าหน้าเว็บตัดการเชื่อมต่อ → 02 ยกเลิก request ไป 03 และบันทึกข้อความเท่าที่ได้เป็น `cancelled`
- สถานะข้อความ: `complete` / `interrupted` / `cancelled`

### 6.3 ต้องยืนยันกับ 03
- tool ของ Agent เรียก 04/05/06 **ตรง** ไม่วนกลับผ่าน 02
- รายชื่อ tool ที่อยู่ใน allowlist
- 03 รองรับการถูกยกเลิกกลาง stream

---

## 7. ฐานข้อมูล

ตารางที่ 02 เป็นเจ้าของ: `students`, `student_preferences`, `plans`, `plan_items`, `chat_sessions`, `chat_messages`, `feedback`

- `chat_messages` มีคอลัมน์ `status`, `sources` (JSONB)
- `plans` มี unique `(student_id, term, name)` → ชนแล้วคืน `CONFLICT_409`
- **feedback**: 02 เป็นเจ้าของ record หลัก แล้วส่งสำเนาไป 08 แบบไม่บล็อก
- seed script สร้างนักศึกษาจำลองตาม `DEMO_STUDENT_ID` + แผนตัวอย่าง 1 แผน
- migration ด้วย Alembic, ทดสอบ migration บน Postgres ใน CI

### Log ไป 08
- ใช้ queue ในหน่วยความจำขนาดจำกัด (1,000 รายการ) ส่งเป็นชุดทุก 2 วินาที
- queue เต็มหรือ 08 ล่ม → ทิ้ง log และนับใน metrics `log_dropped_total` ไม่บล็อกผู้ใช้
- ตอน shutdown พยายาม flush ภายใน 3 วินาที

---

## 8. แผนงานรายวัน (Vertical Slice)

แต่ละ slice **เสร็จ** เมื่อ:
1. 01 เรียกจากหน้าจริงได้ (mock หรือของจริง)
2. มี fixture success/error อัปเดตใน `fixtures/`
3. มี test อย่างน้อย 3 เคส: สำเร็จ / ไม่ได้ล็อกอิน / ปลายทางล่ม (หรือข้อมูลผิด)
4. CI ผ่าน

### D1 — Slice 0 + Slice 1: โครง, สัญญา, ล็อกอิน
- [x] โครงโฟลเดอร์ (`src/`), config จาก env, `.env.example`
- [x] envelope + error handler + รหัส error ทั้งหมด + middleware request-id/`took_ms`
- [x] **Pydantic schema ของทุก endpoint** (แม้ยังไม่ implement) → เปิด `/docs` ให้ 01 ดู OpenAPI
- [x] fixture JSON ชุดแรก + SSE fixture ครบทุก event
- [x] adapter interface + mock ของทุกโมดูล (Prompt 3 — mock + http เสร็จ, inprocess เป็น loader พร้อมใช้แต่ยัง
  เรียกจริงไม่ได้เพราะ 04/05 ยังไม่มีโค้ดใน GitHub — ดู PROGRESS.md)
- [x] ล็อกอินเดโม `admin` / `admin1234`, `/auth/me`, `/auth/logout`, CORS (Prompt 4 — ยืนยันแล้วกับ Postgres
  จริง: pytest 99 passed 1 skipped + curl login/me/logout ผ่านครบผ่าน uvicorn จริง ดู PROGRESS.md)
- [x] Dockerfile + compose (api + postgres + redis), `/health` (Prompt 5 — Dockerfile ใช้ `entrypoint.sh`
  แล้ว, `docker build` + `docker run` จริงยืนยัน `/health`+login ผ่านครบ; ไม่มี `docker-compose.yml` ให้ทดสอบ
  ในสภาพแวดล้อมนี้เพราะเป็นไฟล์ root ของทีมอื่น — ใช้ `docker run` ตรงแทนในการยืนยัน)
- [x] ข้อเสนอ compose + CI ใน `handoff/` (02 ไม่แก้ไฟล์ส่วนกลางเอง) + script รัน lint/test บน Postgres ในเครื่อง
  (Prompt 5 — `handoff/compose.md`, `handoff/ci.md`, `scripts/test.sh` เสร็จและทดสอบรันจริงแล้ว)
- **ส่งมอบ:** 01 ล็อกอินได้จริง และเห็น OpenAPI ครบ

### D2 — Slice 2: วิชา
- [x] `GET /courses`, `GET /courses/{code}/sections` ผ่าน adapter 04 (ตอนนี้ adapter เป็น mock —
  ต้องล็อกอิน, cursor pagination ยืนยันด้วย test จริง)
- [x] cache Redis 10 นาที (ถ้า Redis ล่ม ให้ข้าม cache ไม่ error) — ทดสอบ cache hit + Redis ล่มแล้ว
- **ส่งมอบ:** 01 ค้นวิชาและเลือก section ได้ (ผ่าน mock adapter 04 จนกว่าจะมี 04 จริง)

### D3 — Slice 3: แผนการเรียน
- [x] SQLAlchemy models + migration ของ `plans`, `plan_items` (migration 0002)
- [x] `POST /plans/validate` ผ่าน adapter 05 → 06 (+ ตรวจ section มีจริงผ่าน 04 ก่อน)
- [x] `POST /plans`, `GET /plans`, `GET /plans/{id}`, `DELETE /plans/{id}`
- [x] test ownership: เข้าถึงแผนของ student_id อื่นไม่ได้ (403 ยืนยันด้วย Postgres จริง)
- **ส่งมอบ:** เลือก section → ตรวจ → บันทึก → เปิดแผนเดิมหลัง reload ได้ (ยืนยันด้วย curl จริงกับ Postgres แล้ว)

### D4 — Slice 4: แชต
- [x] models ของ `chat_sessions`, `chat_messages` (migration 0003)
- [x] masking + ตัวกรองข้อความก่อนส่ง 03 (scrub_text บน query/history, ส่งแต่ id_hash)
- [x] `POST /chat` SSE ตามหัวข้อ 6.2 (allowlist, error event, cancel, interrupted) — ยืนยันด้วย Postgres จริง
- [x] `GET /chat/sessions`, `GET /chat/sessions/{id}/messages`
- [x] test: stream ปกติ, 03 ล่มก่อนเริ่ม (502), 03 ตัดกลางทาง (error event), ผู้ใช้ยกเลิก (cancelled) + อีก 7 เคส
- **ส่งมอบ:** แชตได้ เห็น sources และเปิดประวัติเดิมได้ (ยืนยันด้วย capture จริงจาก endpoint ลง fixtures แล้ว)

### D5 — Slice 5: ฟีเจอร์ตาม scope ที่ทีมยืนยัน
- [x] `GET /students/me/profile`, `GET /students/me/transcript`, `POST /students/me/import`
- [x] `POST /plans/auto`, `GET /plans/{id}/explain`
- [x] `POST /feedback` + ส่งต่อ 08 ผ่าน queue (log_queue.py)
- [ ] เปลี่ยน adapter จาก mock เป็นของจริงตามโมดูลที่พร้อม (ยังไม่มีโมดูลไหนพร้อมจริงเลย — ทุก ADAPTER
  ยังเป็น mock ทั้งหมด รอ 04-08 มีโค้ดจริงก่อน)
- **ส่งมอบ:** feature freeze — ทุก endpoint ใน PLAN.md 4.3 implement ครบแล้ว ไม่มีตัวไหนคืน 501 อีก
  (ยืนยันด้วย OpenAPI schema จริง + smoke test ผ่าน server จริงกับ Postgres ครบทุก endpoint)

### D6 — Slice 6: ความเรียบร้อยและรวมระบบ
- [x] rate limit ด้วย Redis (ทั่วไป 60/นาที, แชต 10/นาที, login 5/นาที) — FastAPI dependency (ไม่ใช่ raw
      middleware) ที่ `src/core/rate_limit.py`; Redis ล่ม → fail open + log warning; ทดสอบใน `tests/api/test_rate_limit.py`
- [x] `/ready` ตรวจ Postgres + Redis + โมดูลที่ตั้งเป็น `http` (04-08) + 03 เสมอ; `/metrics`
      (Prometheus ผ่าน `prometheus-fastapi-instrumentator` รวม `log_dropped_total`) — ทดสอบ logic ล้วนๆ
      ใน `tests/unit/test_readiness_service.py` (ไม่ทดสอบ `/ready` ผ่าน HTTP เพราะ endpoint นี้เรียก
      `get_engine()`/`get_redis()` ตรงโดยตั้งใจ ไม่ผ่าน `Depends()` จึง override ใน test ไม่ได้ — ควรสะท้อน
      สถานะ infra จริงเสมอ) และ `tests/api/test_meta_endpoints.py` สำหรับ `/health`, `/metrics`
- [x] ปักเวอร์ชัน dependency (lock file) — `requirements.lock` (pip freeze จาก venv สะอาดที่ติดตั้งเฉพาะ
      `requirements.txt`); `Dockerfile` ติดตั้งจากไฟล์นี้แทน `requirements.txt` ตรง ๆ; verify แล้วว่า
      `docker build` สำเร็จจริงด้วย lock file นี้
- [x] clean clone → `docker compose up` → flow จาก UI ครบบนเครื่องใหม่ — ไม่มี `docker-compose.yml` ที่
      root ของ repo นี้ (ข้อเสนออยู่ที่ `handoff/compose.md`) จึงจำลองด้วย `scripts/smoke.sh` แทน: build
      image จริง + Postgres/Redis จริงผ่าน `docker network` + curl ครบ flow login→courses→validate→
      save→chat — รันผ่านจริงแล้ว (chat ได้ `UPSTREAM_502` ตามคาด เพราะยังไม่มี router 03 จริงให้ต่อ)
- [x] เขียน `handoff/api-spec.md` จาก OpenAPI (+ export `handoff/openapi.json` จริงจาก `app.openapi()`)
      + อัปเดต `01_env.txt`, `02_step.txt`, `03_process.txt` ให้ตรงโค้ดจริง (เดิมยังอ้าง `app/` และชื่อ
      env ตัวเก่า) + เพิ่ม `README.md` ระดับโมดูล

### D7 — Buffer
- [x] แก้ bug จากการรวมระบบ, ตรวจรอบสุดท้าย, เตรียมเดโม — เทียบ §4.3 กับ OpenAPI จริงครบ (0 endpoint
      เป็น 501), ไล่ checkbox §8 ทั้งหมด, ตรวจความปลอดภัย (log ไม่มี PII, cookie flags, CORS validator,
      ไม่มี secret/.env ในโปรเจกต์, ไม่มีรหัส นศ. รูปแบบจริงนอก tests/fixtures — เพิ่ม `.gitignore` กัน
      หลุดตอน commit ครั้งแรก), `pytest -q` (190 passed, 2 skipped) + `ruff check .` + `scripts/smoke.sh`
      ผ่านหมด ไม่มี "git diff" ให้ตรวจเพราะยังไม่มี git repo ในสภาพแวดล้อมนี้ (ยืนยันด้วยการตรวจ `E:\ML`
      ว่ามีแค่โฟลเดอร์ `02_api_backend/` เท่านั้น ไม่มีไฟล์ใดถูกสร้าง/แก้นอกโมดูลเลย)
- [x] สรุปรายการที่ยังเป็น mock ให้ชัดในเอกสารส่งงาน — ดู `handoff/HANDOFF.md`

---

## 9. การทดสอบ

| ระดับ | ทดสอบอะไร | ที่ไหน |
|---|---|---|
| Unit | masking, แปลงเวลา, envelope, retry policy | pytest (ไม่ต้องใช้ DB) |
| API | ทุก endpoint 3 เคสขึ้นไป + ownership | pytest + Postgres ใน CI |
| Contract | response ตรง schema และ fixture ที่ 01 ใช้ | pytest เทียบกับ `fixtures/` |
| SSE | ลำดับ event, error, cancel, ภาษาไทยข้าม chunk | pytest + httpx stream |
| E2E | login → วิชา → ตรวจแผน → บันทึก → แชต จากหน้าเว็บจริง | ร่วมกับ 01 ใน D6 |

---

## 10. ไม่ทำในรอบนี้

- ระบบหลายบัญชี / หลาย role (advisor / admin จริง) และการยืนยันตัวตนกับระบบมหาวิทยาลัย
- ส่งออก `.ics` และแจ้งเตือน (งานของ 08)
- scrape ระบบทะเบียน (`ALLOW_SCRAPING=false`)

---

## 11. สิ่งที่ 02 ส่งให้ทีม

| ถึง | สิ่งที่ส่ง | ภายใน |
|---|---|---|
| 01 | OpenAPI (`/docs`), fixtures, บัญชีเดโม, CORS/cookie policy | D1 |
| 01, 03 | SSE fixtures ครบทุก event รวม error/cancel | D1 |
| 03 | enriched JSON schema + allowlist ของ tool | D1 |
| 04–07 | adapter interface ที่ 02 คาดหวัง (input/output) | D1 |
| 08 | รูปแบบ log, compose, env convention | D2 |

---

## 12. คำถามถึงทีม

- [ ] วันเริ่ม D1 และวันส่งจริง
- [ ] ค่าเริ่มต้นของ adapter 04–07: `inprocess` (container เดียว) หรือ `http` (หลาย services)?
- [ ] เจ้าของ 03 รับ enriched JSON, SSE event และนโยบาย cancel ในหัวข้อ 6 ได้ไหม
- [ ] เจ้าของคลังความรู้ยืนยัน fields ของ sources (`document_id`, `url`) ได้ไหม
- [ ] เกณฑ์ประเมินบังคับ import HTML และ auto plan เป็น P0 หรือไม่
- [ ] module map 04–08 ฉบับเดียวที่ทุกคนใช้
