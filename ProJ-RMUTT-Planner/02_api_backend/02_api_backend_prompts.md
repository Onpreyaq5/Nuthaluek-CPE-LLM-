# Prompts สำหรับ Claude Code — 02_api_backend (v2)

อิง `PLAN.md` ฉบับปรับปรุง · 11 prompt แบ่งตามวัน D1–D7 · 1 prompt = 1 commit

**ขอบเขต: ทุก prompt แก้เฉพาะใน `02_api_backend/`** — ไฟล์ส่วนกลาง (compose, CI, 00_docs) จะเขียนเป็นข้อเสนอไว้ใน `02_api_backend/handoff/` ให้ทีมเอาไปใช้เอง

| วัน | Prompt | Slice |
|---|---|---|
| D1 | 1 โครง + core · 2 schema + fixtures · 3 adapters · 4 DB + auth · 5 Docker + handoff | 0, 1 |
| D2 | 6 วิชา | 2 |
| D3 | 7 แผนการเรียน | 3 |
| D4 | 8 แชต SSE | 4 |
| D5 | 9 นักศึกษา / import / auto / feedback | 5 |
| D6 | 10 ความเรียบร้อย + เอกสาร | 6 |
| D7 | 11 ตรวจรอบสุดท้าย | buffer |

## เตรียมก่อนเริ่ม
1. วาง `CLAUDE.md` และ `PLAN.md` ใน `02_api_backend/`
2. `git checkout main && git pull origin main` (ทำงานตรงบน `main` ตาม `CONTRIBUTING.md` ของทีม —
   ไม่ต้องสร้าง branch/PR)
3. เปิด Claude Code ที่ root ของ `ProJ-RMUTT-Planner`
4. ทำทีละ prompt → ตรวจ `pytest -q` + เปิด `http://localhost:8000/docs` → `/clear` → prompt ถัดไป

---

## Prompt 1 — โครงโปรเจกต์ + core (D1)

```text
อ่าน 02_api_backend/CLAUDE.md และ PLAN.md หัวข้อ 3–4 ก่อน

เป้าหมาย: โครง FastAPI ที่ทุก endpoint ใช้ร่วมกัน ยังไม่มี endpoint ธุรกิจ

1. คงโฟลเดอร์ src/ เดิม สร้างโครงย่อยใต้ src/ ตาม CLAUDE.md (src/main.py เดิมมีแค่ /health — ขยายต่อจากไฟล์นี้)
   Dockerfile คง CMD uvicorn src.main:app ไว้
2. src/core/config.py — pydantic-settings อ่าน env ทุกตัวใน PLAN.md (หัวข้อ 3.2, 5) และ DATABASE_URL, REDIS_URL, LOG_LEVEL
   (ตั้ง default ให้รันได้แม้ root compose ยังไม่ส่ง env ใหม่ เช่น ADAPTER_* = mock)
   รวมค่า timeout ตาราง 3.3 เป็น setting แยกตามประเภทคำขอ
3. 02_api_backend/.env.example (ในโมดูล ไม่ใช่ที่ root) — ครบทุก env พร้อมค่าเริ่มต้นตาม PLAN.md
4. src/core/errors.py — AppError + subclass ครบทุก code ใน CLAUDE.md พร้อม HTTP status
   handler แปลง RequestValidationError → VALIDATION_422, exception อื่น → INTERNAL_500 (ไม่หลุด stack trace)
5. src/core/envelope.py — success/error envelope ที่มี meta{request_id, took_ms} ทั้งสองแบบ
6. middleware — request_id (รับ X-Request-ID ถ้ามี ไม่งั้นสร้าง "req_" + สุ่ม), จับเวลา, ใส่ header X-Request-ID ทุก response
   เก็บใน contextvar ให้ envelope และ logger ใช้
7. src/core/logging.py — structlog JSON มี request_id ทุกบรรทัด
8. src/core/masking.py
   - hash_student_id(id) → HMAC-SHA256 ด้วย JWT_SECRET ตัด 16 ตัวแรก
   - scrub_text(text) → แทนรหัสนักศึกษา (รูปแบบ 12หลัก-1หลัก, 13 หลัก และ 10 หลัก), เบอร์โทรไทย, อีเมล ด้วย placeholder
   - mask_payload(dict) → ลบ/แทน key: name_th, name_en, student_id, password, username
9. src/main.py — ประกอบทุกอย่าง, CORS จาก CORS_ORIGINS (allow_credentials=True ห้ามใช้ "*"), GET /health, router ว่าง /api/v1
10. requirements.txt, requirements-dev.txt (pytest, pytest-asyncio, fakeredis, ruff), ruff config ใน pyproject.toml
11. tests/unit: envelope ทั้งสองแบบ, handler ทุก code ได้ HTTP status ถูก, X-Request-ID, masking ทุกรูปแบบ
    (ห้ามใส่รหัสรูปแบบจริงในไฟล์ test นอก tests/fixtures/ — สร้าง string ตอน runtime แทน)
    tests/conftest.py: marker "db" — ถ้าไม่มี TEST_DATABASE_URL ให้ skip test ที่ใช้ DB

เงื่อนไขเสร็จ: pytest + ruff ผ่าน, uvicorn src.main:app รันได้, /health 200
commit "[02] วางโครง src/ + envelope + errors + middleware + masking"
```

---

## Prompt 2 — Schema ทุก endpoint + fixtures (D1)

```text
อ่าน 02_api_backend/CLAUDE.md, PLAN.md หัวข้อ 4, 6 และ 06_schedule_conflict_engine/03_process.txt ก่อน

เป้าหมาย: สัญญาของทุก endpoint ใน PLAN.md 4.3 ให้ 01 เห็นใน /docs ได้ทันทีแม้ยังไม่ implement

1. src/schemas/common.py — Day enum, เวลา "HH:MM", Term ("1/2569" รูปแบบ ภาค/ปีพ.ศ.), Cursor page generic
   {items, next_cursor}, helper แปลง นาที<->HH:MM และ 0..6<->Day
2. schema แยกไฟล์ตามหมวด ครบทุกแถวในตาราง 4.3 (รวม 🆕: GET/DELETE /plans/{id}, /chat/sessions, /chat/sessions/{id}/messages)
   - section_id เป็น str, ID อื่นเป็น int
   - /plans/validate response ตรง RESPONSE CONTRACT ของ 06 ทุกฟิลด์
   - chat: EnrichedChatRequest ตาม 6.1 (extra="forbid", ไม่มีชื่อ/รหัสจริง)
   - SSE event: discriminated union ตาม "type" = session | tool_start | tool_end | token | sources | done | error
     sources item มี title, section, page, document_id, url
   - message status enum: complete | interrupted | cancelled
3. ทุก schema มี example ใน json_schema_extra
4. src/api/v1/ — router stub ของทุก endpoint ประกาศ request/response model ครบ
   ตัวที่ยังไม่ทำคืน HTTP 501 ผ่าน envelope (code NOT_IMPLEMENTED_501 — เพิ่มใน errors)
   /docs ต้องแสดงครบทุก endpoint
5. fixtures/ — JSON ตัวอย่าง success และ error ของทุก endpoint (ชื่อไฟล์ <หมวด>/<endpoint>.<case>.json)
   fixtures/sse/ — ลำดับ event ปกติ, error กลางทาง, ปิดโดยไม่มี done, sources ภาษาไทย
6. tests/contract: ทุก fixture validate ผ่าน schema ที่ตรงกัน

ถ้า PLAN.md ขัดกับ 03_process.txt ของ 06 ให้ยึด 06 และบันทึกไว้ในสรุป
commit "[02] เพิ่ม schema + router stub ของทุก endpoint และ fixtures"
```

---

## Prompt 3 — Adapter interface + mock / http / inprocess (D1)

```text
อ่าน 02_api_backend/CLAUDE.md, PLAN.md หัวข้อ 3.2–3.3 และ 00_docs/03_flow.md FLOW A, B, C, F ก่อน

เป้าหมาย: เรียกโมดูล 03–08 ผ่าน interface เดียว สลับ mock/inprocess/http ด้วย env

1. src/adapters/interfaces.py — Protocol ต่อโมดูล (ใช้ schema จาก Prompt 2)
   04 CourseCatalog: search_courses, get_sections(code, term), get_sections_by_ids(ids)
   05 StudentData: get_context(student_id), import_graduate_check(raw: bytes)
   06 PlanEngine: validate(term, section_ids, student), generate(term, preferences, student, must_include)
   07 Explainer: explain_plan(plan, student)
   08 LogSink: send_batch(events), send_feedback(feedback)
   03 ChatRouter: stream(enriched) -> AsyncIterator[event]
2. src/adapters/http_base.py — httpx.AsyncClient ที่รับ timeout/retry ตามประเภทคำขอ (ตาราง 3.3),
   retry เฉพาะ timeout/5xx, ส่งต่อ X-Request-ID, error ทุกแบบ → UpstreamError (UPSTREAM_502, details.module)
3. http implementation ของทุกโมดูล (path ของปลายทางยังไม่มีสัญญา — ใส่ค่าคาดหวังเป็นค่าคงที่ต้นไฟล์ และ list ไว้ในสรุป)
4. mock implementation อ่านจาก fixtures/ + ข้อมูลสังเคราะห์:
   - วิชา ~8 วิชา หลาย section บางคู่ตั้งใจเวลาชน, มี prerequisite, มี section ที่นั่งเต็ม
   - mock 06 ตรวจจริงแบบง่าย: C1 เวลาทับ, C3 prereq ไม่ครบ, C4 หน่วยกิตเกิน 21, C6 ที่นั่งเต็ม
     และ generate คืน 3 แผนที่ไม่ชน
   - mock 03 stream: session → tool_start → tool_end → token หลายตัว (มีภาษาไทย) → sources → done หน่วงสั้นๆ
     และโหมดจำลองล่มกลางทางเมื่อข้อความมีคำว่า "__fail__"
5. inprocess — ทำเฉพาะ 04 และ 05 ที่มี parser แล้ว
   ปัญหา: โฟลเดอร์ขึ้นต้นด้วยตัวเลขและทั้งคู่ชื่อแพ็กเกจ src (ชนกัน) และใช้ relative import
   วิธี: src/adapters/inprocess_loader.py โหลด <module>/src เป็นแพ็กเกจชื่อไม่ซ้ำ (mod04, mod05)
   ด้วย importlib.util.spec_from_file_location(..., submodule_search_locations=[path]) แล้ว register ใน sys.modules
   path อ่านจาก env MODULES_ROOT (default: parent ของ 02_api_backend) — อ่านโค้ดของ 04/05 อย่างเดียว ห้ามแก้
   หมายเหตุ: ใน Docker ใช้ไม่ได้จนกว่าทีมจะเปลี่ยน build context (บันทึกไว้ใน handoff ของ Prompt 5)
   - 05 import_graduate_check → mod05.graduate_check.parse_graduate_check + mod05.degree_plan.build_plan_input
     ทิ้ง student_id ที่ parse ได้จากไฟล์ ใช้ของ session แทน
   - 04 ใช้ mod04.adapters.oreg_rmutt เท่าที่มี ส่วนที่ไม่มีฟังก์ชันรองรับ raise NotImplementedError พร้อมข้อความชัด
6. src/adapters/__init__.py — factory ตาม ADAPTER_04..08 เป็น FastAPI dependency (override ใน test ได้)
7. tests/unit: retry/timeout (httpx.MockTransport), UpstreamError, mock 06 ตรวจครบทุกกรณี,
   inprocess โหลด 05 แล้ว parse 05_data_integration/tests/fixtures/graduate_check_sample.html ได้
   (ต้องติดตั้ง beautifulsoup4, lxml เพิ่มใน requirements)

ห้าม network จริงใน test · ค่าเริ่มต้นทุก ADAPTER = mock
commit "[02] เพิ่ม adapter interface + mock/http/inprocess"
```

---

## Prompt 4 — ฐานข้อมูล + ล็อกอินเดโม (D1)

```text
อ่าน 02_api_backend/CLAUDE.md, PLAN.md หัวข้อ 5 และ 7 และ 00_docs/05_data_model.md ก่อน

เป้าหมาย: 01 ล็อกอินด้วย admin/admin1234 ได้จริง

1. src/core/db.py — async engine + session dependency
2. models: students, student_preferences (ตาม 05_data_model.md) — ตารางอื่นทำใน slice ของมัน
3. Alembic แบบ async ใน migrations/ + migration แรก
   (infra/db/001_init.sql เป็น placeholder ไม่มีตาราง — 02 เป็นเจ้าของตารางของตัวเองผ่าน Alembic)
4. scripts/seed_demo.py — นักศึกษาสังเคราะห์ตาม DEMO_STUDENT_ID + preferences (idempotent รันซ้ำได้)
5. src/core/security.py — JWT HS256 อายุ JWT_EXPIRE_MINUTES, payload: sub=student_id, username, role
6. endpoints ตาม PLAN.md 5:
   POST /api/v1/auth/login {username, password} → compare_digest กับ env → ตั้ง cookie "session"
     ผิด → AUTH_401 ข้อความเดียว "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" ทุกกรณี
     ห้ามคืน token ใน body
   GET /api/v1/auth/me → {username, student_id, role}
   POST /api/v1/auth/logout → ลบ cookie
7. dependency current_user: ไม่มี/หมดอายุ/ปลอม → AUTH_401 · คืน student_id, username, role, id_hash
   และ helper ensure_owner(resource_student_id) → FORBIDDEN_403
8. tests/conftest.py: fixture DB บน TEST_DATABASE_URL (สร้าง schema ด้วย alembic upgrade head ต่อ session, truncate ต่อ test),
   fixture client ที่ล็อกอินแล้ว
9. tests/api: login สำเร็จได้ cookie HttpOnly, รหัสผิด, username ผิด (ข้อความเหมือนกัน), /me ไม่มี cookie,
   token หมดอายุ, token ปลอม, logout, body ไม่มี token

commit "[02] เพิ่ม DB, migration, seed และล็อกอินเดโม"
```

---

## Prompt 5 — Docker + ข้อเสนอสำหรับทีม (D1)

```text
อ่าน 02_api_backend/CLAUDE.md, docker-compose.yml และ ../.github/workflows/ci.yml ก่อน (อ่านอย่างเดียว)

เป้าหมาย: 02 รันด้วย compose เดิมได้ และเตรียมข้อเสนอแก้ไฟล์ส่วนกลางให้ทีม โดยไม่แตะไฟล์นอก 02_api_backend

1. 02_api_backend/entrypoint.sh — alembic upgrade head → seed (ถ้า SEED_DEMO=true) → uvicorn src.main:app
   Dockerfile ใช้ entrypoint นี้ (COPY เฉพาะของใน 02_api_backend เพราะ build context คือโฟลเดอร์นี้)
2. ทดสอบกับ compose เดิมโดยไม่แก้: docker compose up -d --build api_backend postgres redis
   → /health 200 → login ผ่าน curl ได้
   ถ้า env ที่ compose ส่งมาไม่พอ ให้ config ใช้ค่า default ที่ปลอดภัยสำหรับเดโม (ไม่ใช่แก้ compose)
3. 02_api_backend/handoff/compose.md — ข้อเสนอให้ทีมแก้ docker-compose.yml และ .env.example ที่ root:
   env ที่ api_backend ต้องการเพิ่ม (ADAPTER_*, DEMO_*, JWT_EXPIRE_MINUTES, ROUTER_URL, SEED_DEMO) พร้อม snippet
   และระบุจุดขัดกัน: PLAN.md ใช้ ROUTER_URL=http://router:8001, CORS localhost:5173
   แต่ compose ใช้ ai_router:8100 และ web_app พอร์ต 3000 — เขียนเป็นคำถามให้ทีมเลือก ห้ามตัดสินเอง
   และเรื่อง inprocess ใน Docker ต้องเปลี่ยน build context เป็น root (ผลกระทบ + snippet)
4. 02_api_backend/handoff/ci.md — ข้อเสนอเพิ่ม job "api-backend" ใน ci.yml: postgres:16-alpine เป็น service container,
   ติดตั้ง requirements + requirements-dev → ruff → pytest (ตั้ง TEST_DATABASE_URL) พร้อม YAML เต็ม
   หมายเหตุ: syntax check เดิม (0*/src) ครอบ 02 อยู่แล้วเพราะเราใช้ src/
   และบอกว่าตอนนี้ CI ยังไม่รัน test ของ 02 จนกว่าทีมจะรับข้อเสนอนี้
5. 02_api_backend/Makefile หรือ scripts/test.sh — รัน postgres ด้วย docker compose แล้ว pytest + ruff คำสั่งเดียว
   (ใช้แทน CI ระหว่างรอ)

commit "[02] เพิ่ม entrypoint, test script และข้อเสนอ compose/CI ใน handoff"
สรุปท้าย: สิ่งที่ส่งมอบ D1 ครบตาม PLAN.md หัวข้อ 11 หรือยัง
```

---

## Prompt 6 — Slice 2: วิชา (D2)

```text
อ่าน 02_api_backend/CLAUDE.md และ PLAN.md หัวข้อ 4.3, 8 (D2) ก่อน

1. GET /api/v1/courses?q=&term=&day=&teacher=&cursor=&limit= — ผ่าน adapter 04, cursor pagination
2. GET /api/v1/courses/{code}/sections?term= — ไม่พบ → NOT_FOUND_404
3. cache Redis 10 นาที (key = hash ของ query ทั้งหมด) · Redis ล่ม → ข้าม cache + log warning ไม่ error
4. ต้องล็อกอิน · แทนที่ stub 501 ของสองตัวนี้
5. อัปเดต fixtures/courses/*
6. tests: สำเร็จ, ไม่ล็อกอิน, 04 ล่ม → 502, ไม่พบวิชา, cache hit (adapter ถูกเรียกครั้งเดียว — fakeredis), Redis ล่ม, pagination

commit "[02] slice 2: courses + sections + cache"
```

---

## Prompt 7 — Slice 3: แผนการเรียน (D3)

```text
อ่าน 02_api_backend/CLAUDE.md, PLAN.md หัวข้อ 7, 8 (D3), 00_docs/03_flow.md FLOW A และ 06_schedule_conflict_engine/03_process.txt ก่อน

1. models + migration: plans (unique student_id, term, name), plan_items (section_id เป็น string ไม่มี FK — ตาราง sections เป็นของ 04/05)
2. POST /api/v1/plans/validate {term, section_ids[]}
   adapter 05 get_context → adapter 06 validate → ส่งผลต่อตามเดิม (02 ห้ามตัดสินเอง)
   section_ids ว่างหรือเกิน 15 → VALIDATION_422 · id ไม่มีจริง → NOT_FOUND_404 ระบุใน details
3. POST /plans (ชื่อซ้ำ → CONFLICT_409), GET /plans?term= (cursor), GET /plans/{id} (section + คาบ + ผลตรวจล่าสุด),
   DELETE /plans/{id}
4. ownership: แผนของ student_id อื่น → FORBIDDEN_403 ทุก endpoint
5. seed: เพิ่มแผนตัวอย่าง 1 แผนให้บัญชีเดโม
6. อัปเดต fixtures/plans/*
7. tests: ไม่ชน, C1, C3, section ไม่มีจริง, 06 ล่ม → 502, บันทึก/อ่าน/ลบ, ชื่อซ้ำ, ownership ทุก endpoint
   (สร้างนักศึกษาคนที่สองใน test เพื่อทดสอบ)

ส่งมอบ: เลือก section → ตรวจ → บันทึก → เปิดแผนเดิมหลัง reload ได้
commit "[02] slice 3: plans validate + CRUD"
```

---

## Prompt 8 — Slice 4: แชต SSE (D4)

```text
อ่าน 02_api_backend/CLAUDE.md, PLAN.md หัวข้อ 6 ทั้งหมด, 8 (D4) และ 03_ai_router_agent/03_process.txt ก่อน

1. models + migration: chat_sessions, chat_messages (status, sources JSONB, intent, latency_ms)
2. POST /api/v1/chat {session_id | null, message, plan_draft} → text/event-stream
   ก่อนเริ่ม stream (ผิดตรงนี้คืน HTTP error ตาม envelope):
   - session_id ของคนอื่น → FORBIDDEN_403 · ไม่มีจริง → NOT_FOUND_404 · null → สร้างใหม่
   - บันทึกข้อความผู้ใช้
   - สร้าง EnrichedChatRequest: history = 10 ข้อความล่าสุดที่ status complete,
     query/history ผ่าน scrub_text, student ใช้ id_hash เท่านั้น
   ระหว่าง stream:
   - event แรกเป็น session เสมอ
   - ส่งต่อเฉพาะ event ในตาราง 6.2 · tool_start/tool_end ส่งเฉพาะชื่อใน allowlist (config TOOL_ALLOWLIST
     ค่าเริ่มต้นจาก INTENT → TOOL MAP ใน 03_process.txt) และตัด arguments ทิ้ง · sources ตรวจ schema ก่อน
   - timeout: รอเริ่ม 15s, idle 30s, รวม 120s
   - format: "data: <json>\n\n" · headers Content-Type, Cache-Control: no-cache, X-Accel-Buffering: no
   - ระวังภาษาไทยข้าม chunk: decode stream จาก 03 ด้วย incremental UTF-8 decoder
   จบ:
   - done → บันทึก assistant message status complete + sources
   - 03 ปิดโดยไม่มี done / ล่มกลางทาง → ส่ง error event UPSTREAM_502 แล้วบันทึก interrupted
   - client ตัดการเชื่อมต่อ → ยกเลิก request ไป 03, บันทึก cancelled
3. GET /api/v1/chat/sessions (ใหม่สุดก่อน, cursor), GET /api/v1/chat/sessions/{id}/messages (cursor, ownership)
4. อัปเดต fixtures/sse/* ให้ตรงของจริง
5. tests/sse: ลำดับ event ปกติ, session ใหม่, 03 ล่มก่อนเริ่ม (HTTP 502), 03 ตัดกลางทาง, ผู้ใช้ยกเลิก,
   event นอกตารางถูกทิ้ง, arguments ถูกตัด, tool นอก allowlist ถูกทิ้ง, ภาษาไทยข้าม chunk ไม่เพี้ยน,
   payload ที่ส่งไป 03 ไม่มีรหัส/ชื่อจริง (ตรวจจาก mock), history ข้ามข้อความที่ไม่ complete

commit "[02] slice 4: chat SSE + sessions + history"
```

---

## Prompt 9 — Slice 5: นักศึกษา, import, auto plan, feedback (D5)

```text
อ่าน 02_api_backend/CLAUDE.md, PLAN.md หัวข้อ 4.4, 7, 8 (D5), 00_docs/03_flow.md FLOW B, F ก่อน

1. GET /api/v1/students/me/profile (DB + adapter 05), GET /api/v1/students/me/transcript (adapter 05)
2. POST /api/v1/students/me/import — multipart field "file"
   - เกิน 2 MB → PAYLOAD_413 (ตรวจระหว่างอ่าน ไม่อ่านทั้งไฟล์ก่อน)
   - ตรวจเนื้อหาว่าเป็น HTML จริง ไม่เชื่อนามสกุล/content-type อย่างเดียว → ไม่ใช่ → VALIDATION_422
   - ส่ง adapter 05 · ไม่บันทึกไฟล์ลงดิสก์ · ไม่ log เนื้อหา
   - คืน imported_courses, retake_required, credits_remaining, warnings
   - fixtures/import/sample_sanitized.html + expected.json (สร้างจากไฟล์ตัวอย่างของ 05 ที่ลบข้อมูลระบุตัวตนแล้ว)
3. POST /api/v1/plans/auto {term, preferences?, must_include?, exclude?}
   05 context → 06 generate → 07 explain ทีละแผน · ไม่ส่ง preferences ใช้ของ DB
   07 ล่ม → คืนแผนโดย explanation=null + warning (ไม่ล้มทั้ง request) · ไม่ retry ตามตาราง 3.3
4. GET /api/v1/plans/{id}/explain (ownership)
5. model feedback + migration · POST /api/v1/feedback — ตรวจว่า target เป็นของผู้ใช้ → บันทึก DB → ส่งสำเนา 08
6. src/core/log_queue.py ตาม PLAN.md 7: queue 1,000 รายการ, ส่งเป็นชุดทุก 2 วินาทีผ่าน adapter 08,
   เต็ม/08 ล่ม → ทิ้งและนับ log_dropped_total, flush ภายใน 3 วินาทีตอน shutdown (lifespan)
   ใช้กับ validate, auto, chat, feedback (payload ผ่าน mask_payload, ไม่มีเนื้อข้อความ)
7. tests: ทุก endpoint 3 เคสขึ้นไป + ไฟล์ใหญ่, ไฟล์ไม่ใช่ HTML, import ด้วย inprocess 05 ได้ผลตรง expected.json,
   auto ตอน 07 ล่ม, feedback ของคนอื่น → 403, queue เต็มนับ dropped, flush ตอน shutdown

commit "[02] slice 5: students, import, auto plan, explain, feedback + log queue"
สรุปท้าย: adapter ไหนเปลี่ยนเป็นของจริงได้แล้ว อันไหนยังเป็น mock เพราะอะไร
```

---

## Prompt 10 — Slice 6: ความเรียบร้อย + เอกสาร (D6)

```text
อ่าน 02_api_backend/CLAUDE.md, PLAN.md หัวข้อ 8 (D6), 9 และ 00_docs/04_team_roles.md (Definition of Done) ก่อน

1. rate limit Redis fixed window: ทั่วไป 60/นาที ต่อ student_id, /chat 10/นาที, /auth/login 5/นาที ต่อ IP
   เกิน → RATE_429 + Retry-After · Redis ล่ม → fail open + log
2. GET /ready — Postgres, Redis และเฉพาะโมดูลที่ ADAPTER=http (+ 03) · ไม่พร้อม → 503 พร้อมสถานะรายตัว
3. GET /metrics — Prometheus text (prometheus-fastapi-instrumentator) รวม log_dropped_total
4. ปักเวอร์ชัน dependency (pip-compile หรือ pip freeze เป็น requirements.lock) และให้ Dockerfile ใช้ไฟล์ lock
5. ไล่ตรวจตาราง PLAN.md 9: ทุก endpoint มี 3 เคสขึ้นไป + ownership, contract test ครอบทุก fixture — เติมที่ขาด
6. จำลอง clean clone: git clone ไป /tmp → cp .env.example .env → docker compose up -d --build api_backend postgres redis
   → login → courses → validate → save → chat ผ่าน curl ครบ บันทึกคำสั่งไว้ใน scripts/smoke.sh
7. เอกสาร (ทั้งหมดอยู่ใน 02_api_backend):
   - README.md: วิธีรัน, env, curl ตัวอย่างทุก endpoint, ตาราง adapter
   - อัปเดต 01_env.txt, 02_step.txt, 03_process.txt ให้ตรงโค้ดจริง
   - handoff/api-spec.md สร้างจาก OpenAPI จริง + handoff/openapi.json (export จาก app)
     ให้ทีมย้ายไป 00_docs เองถ้าต้องการ

commit:
"[02] slice 6: rate limit, /ready, /metrics, lock dependencies, smoke test"
"[02] อัปเดตเอกสารโมดูลและ api-spec ใน handoff"
สรุปท้าย: ผ่าน Definition of Done ครบ 5 ข้อหรือยัง
```

---

## Prompt 11 — ตรวจรอบสุดท้าย (D7)

```text
อ่าน 02_api_backend/CLAUDE.md และ PLAN.md ทั้งหมดก่อน — รอบนี้ห้ามเพิ่มฟีเจอร์

1. เทียบ PLAN.md หัวข้อ 4.3 กับ /docs จริง: ทุก endpoint มีครบ ไม่มีตัวไหนยังคืน 501
2. ไล่ checkbox หัวข้อ 8 ทุกข้อ ติ๊กที่เสร็จ ข้อที่ไม่เสร็จเขียนเหตุผลต่อท้าย
3. ตรวจความปลอดภัย: grep หาการ log ที่อาจมีชื่อ/รหัส/เนื้อแชต, cookie flags, CORS ไม่เป็น "*",
   ไม่มี secret ใน repo, ไม่มีรหัสรูปแบบจริงนอก tests/fixtures
4. รัน pytest, ruff, scripts/smoke.sh
   และตรวจ git diff main --stat ว่าไม่มีไฟล์ใดนอก 02_api_backend/ ถูกแก้
5. เขียน 02_api_backend/handoff/HANDOFF.md: สถานะแต่ละ endpoint, adapter ไหนยังเป็น mock, known issues,
   วิธีเดโมทีละขั้นด้วยบัญชี admin

แก้เฉพาะ bug ที่พบ แต่ละ bug commit แยก "[02] fix: ..."
สุดท้าย commit "[02] เพิ่ม HANDOFF.md"
```

---

## หลังจบ
ทำงานตรงบน `main` ตาม `CONTRIBUTING.md` ของทีม (ไม่ใช้ branch/PR):
```bash
git add 02_api_backend/
git commit -m "[02] <สิ่งที่ทำ>"
git pull --rebase origin main
git push origin main
```
แจ้งทีมให้ดูไฟล์ใน `02_api_backend/handoff/` (compose, CI, api-spec) — ส่วนนี้ทีมเป็นคนตัดสินและแก้ไฟล์ส่วนกลางเอง
(ส่งงานรายวันให้ 01 เร็วขึ้นได้ด้วยการ commit+push หลังจบแต่ละวันแทนที่จะรวบท้ายสุด)
