# ความคืบหน้า — 02_api_backend

เอกสารนี้สรุปสิ่งที่ทำไปแล้วจาก `02_api_backend_prompts.md` (v2) ในรูปแบบเดียวกับไฟล์ prompts เดิม
ก็อปทั้งบล็อก ```text``` ของ **"สถานะล่าสุด"** ด้านล่างไปวางเป็นข้อความแรกในแชต Claude Code ใหม่ เพื่อให้ Claude
เข้าใจว่าทำอะไรไปแล้วบ้าง โดยไม่ต้องอ่านโค้ดทั้งหมดใหม่

## ภาพรวมสถานะ (11 prompt, D1–D7)

| Prompt | เนื้อหา | สถานะ |
|---|---|---|
| 1 | โครงโปรเจกต์ + core (`src/core`, envelope, errors, middleware, masking) | ✅ เสร็จ |
| 2 | Schema ทุก endpoint + fixtures + router stub (501) | ✅ เสร็จ |
| 3 | Adapter interface + mock/http/inprocess (03–08) | ✅ เสร็จ (mock+http เต็ม, inprocess รอ 04/05) |
| 4 | ฐานข้อมูล + ล็อกอินเดโม | ✅ เสร็จ ยืนยันกับ Postgres จริงแล้ว |
| 5 | Docker + handoff (compose/CI proposal) | ✅ เสร็จ (D1 จบแล้ว) |
| 6 | Slice 2: วิชา | ✅ เสร็จ (D2 จบแล้ว) |
| 7 | Slice 3: แผนการเรียน | ✅ เสร็จ (D3 จบแล้ว) |
| 8 | Slice 4: แชต SSE | ✅ เสร็จ (D4 จบแล้ว) |
| 9 | Slice 5: นักศึกษา/import/auto/feedback | ✅ เสร็จ (D5 จบแล้ว — ทุก endpoint implement ครบ) |
| 10 | Slice 6: ความเรียบร้อย + เอกสาร | ✅ เสร็จ (D6 จบแล้ว) |
| 11 | ตรวจรอบสุดท้าย | ✅ เสร็จ (D7 จบแล้ว — ครบทั้ง 11 prompt) |

---

## สถานะล่าสุด (paste ให้ Claude Code อ่านก่อนทำต่อ)

```text
สถานะปัจจุบันของ 02_api_backend (อ่าน CLAUDE.md และ PLAN.md ในโฟลเดอร์นี้ก่อนเสมอ):

ทำ Prompt 1-11 เสร็จแล้วครบทั้งหมด (จาก 02_api_backend_prompts.md) = จบ D1-D7 ตาม PLAN.md —
**ทุก endpoint ใน PLAN.md 4.3 implement จริงครบแล้ว ไม่มีตัวไหนคืน 501 อีกต่อไป** งาน "ความเรียบร้อย +
เอกสาร" (D6) และ "ตรวจรอบสุดท้าย" (D7) เสร็จหมดแล้ว มี `handoff/HANDOFF.md` สรุปสถานะ+known issues+
วิธีเดโมให้ทีมอื่นอ่านต่อได้เลย
Prompt 4/5/6/7/8/9/10/11 ยืนยันกับ Postgres/Redis(fakeredis)/Docker จริงแล้ว (ไม่ใช่แค่เขียนโค้ดเฉยๆ):

Prompt 1 — โครงโปรเจกต์ + core:
- src/core/config.py: pydantic-settings อ่าน env ครบ + TimeoutSettings ตามตาราง 3.3
- src/core/errors.py: AppError + subclass ครบทุก code
- src/core/envelope.py, src/core/middleware.py: envelope + request-id middleware + contextvar
- src/core/logging.py: structlog JSON, src/core/masking.py: hash_student_id/scrub_text/mask_payload
- src/main.py: FastAPI app ประกอบทุกอย่าง, CORS, exception handler ครบ, GET /health
- requirements*.txt, pyproject.toml (ruff+pytest), Dockerfile
- tests/unit: envelope, errors, masking

Prompt 2 — Schema ทุก endpoint + fixtures:
- src/schemas/*.py ครบทุก endpoint ใน PLAN.md 4.3 (รวม 🆕 ทั้งหมด) ทุก schema มี example
- src/api/v1/*.py: router ครบ 18 endpoint ทุกตัวคืน 501 NOT_IMPLEMENTED_501 ผ่าน envelope
- fixtures/ ครบ success+error ทุก endpoint + sse/ ครบ 4 กรณี + enriched_request.example.json
- tests/contract: fixture ทุกไฟล์ validate ผ่าน schema จริง

Prompt 3 — Adapter interface + mock/http/inprocess:
- src/adapters/interfaces.py: Protocol ของ 04(CourseCatalog)/05(StudentData)/06(PlanEngine)/
  07(Explainer)/08(LogSink)/03(ChatRouter) + StudentContext model ภายใน
- src/adapters/http_base.py: HttpAdapterClient (httpx) retry เฉพาะ timeout/5xx ตาม TimeoutPolicy
  ต่อประเภทคำขอ, error ทุกแบบ -> Upstream502Error(details={"module":...}), forward X-Request-ID
- src/adapters/http/*.py: http implementation ครบทุกโมดูล (04-08 + 03) — path ปลายทางเป็น
  PLACEHOLDER (ยังไม่มีสัญญาจริงจากทีม 04-08) ระบุเป็นค่าคงที่ต้นไฟล์ทุกไฟล์ (PATH_*)
- src/adapters/mock/*.py: ข้อมูลสังเคราะห์ 8 วิชา/10 section ใน mock/data.py (มีคู่เวลาชน,
  prerequisite ต่อกัน 3 ชั้น, 1 section เต็ม) — MockPlanEngine.validate() ตรวจจริงครบ C1(เวลาทับ)/
  C3(prereq)/C4(หน่วยกิตเกิน21)/C6(ที่นั่งเต็ม), .generate() คืน 3 แผนไม่ชน, MockChatRouter.stream()
  ส่ง event ครบ session->tool_start->tool_end->token(ไทย)->sources->done และ raise ConnectionError
  กลางทางเมื่อ query มีคำว่า "__fail__"
- src/adapters/inprocess_loader.py: loader ทั่วไปใช้ importlib โหลด <module>/src เป็น sys.modules
  ชื่อไม่ซ้ำ (mod04/mod05) อ่านจาก env MODULES_ROOT — เป็น "โครงสร้าง" ที่ใช้งานได้ทันทีที่โมดูลจริงมาถึง
  ตอนนี้ 04/05 ยังไม่มีโค้ดใน GitHub (เพื่อนยังไม่ทำ) เลย src/adapters/inprocess/*.py แค่โหลด loader
  แล้ว raise NotImplementedError ข้อความชัดเจนในทุกเมธอด ยกเว้น InprocessStudentData.import_graduate_check
  ที่ต่อ mod05.graduate_check.parse_graduate_check + mod05.degree_plan.build_plan_input ไว้แล้ว
  (field ของ plan_input ยังไม่ยืนยันกับทีม 05 — ใช้ getattr กันพังไปก่อน)
- src/adapters/__init__.py: factory get_course_catalog()/get_student_data()/get_plan_engine()/
  get_explainer()/get_log_sink()/get_chat_router() เลือก implementation ตาม ADAPTER_04..08
  (03 ใช้ http เสมอ) เป็น FastAPI dependency ธรรมดา override ใน test ได้
- tests/unit: http_base (retry/timeout/4xx passthrough/forward request-id ด้วย httpx.MockTransport),
  inprocess_loader (error ชัดเจนเมื่อไม่พบโมดูล — เทสต์ได้แม้ไม่มี 04/05 จริง), mock ทุกตัว (course_catalog,
  student_data, plan_engine ครบ C1/C3/C4/C6+generate, explainer, log_sink, chat_router รวมโหมด __fail__),
  adapter factory (default ทุกตัว = mock)
- เพิ่ม beautifulsoup4, lxml ใน requirements.txt ตามที่ Prompt 3 ข้อ 7 สั่ง (ไว้รอ 05 มาใช้งานจริง)

Prompt 4 — ฐานข้อมูล + ล็อกอินเดโม:
- src/models/{base,student}.py: SQLAlchemy 2.x Mapped models students(id,student_id,username,role,
  created_at) และ student_preferences(id,student_id FK->students.student_id,free_days JSON,
  no_early_class,max_credits,updated_at) — field เดาไว้เท่าที่ Prompt 4 ต้องใช้ เพราะไม่มีไฟล์
  00_docs/05_data_model.md ในสภาพแวดล้อมนี้ (ดูสมมติฐานด้านล่าง)
- src/core/db.py: get_engine()/get_sessionmaker() แบบ lru_cache (เคลียร์ cache ได้จาก test เพื่อสลับ DB),
  get_db() FastAPI dependency, src/main.py เพิ่ม lifespan dispose engine ตอน shutdown
- alembic.ini, migrations/env.py (async, ตาม cookbook มาตรฐาน), migrations/versions/0001_initial.py
  (handwritten สร้างตาราง students + student_preferences ตรง model)
- scripts/seed_demo.py: upsert บัญชีเดโมตาม DEMO_STUDENT_ID/DEMO_USERNAME แบบ idempotent
- src/core/security.py: create_access_token()/decode_access_token() (JWT HS256, payload sub/username/role,
  อายุ JWT_EXPIRE_MINUTES)
- src/api/deps.py: current_user() dependency (อ่าน cookie "session" -> decode JWT -> AUTH_401 ทุกกรณีผิด/
  หมดอายุ/ไม่มี) คืน CurrentUser(student_id,username,role,id_hash) + ensure_owner() -> FORBIDDEN_403
- src/api/v1/auth.py: implement จริงแทน stub 501 ทั้ง 3 ตัว
  - POST /auth/login: compare_digest กับ env, lookup Student ใน DB, ออก JWT ใส่ cookie "session"
    (HttpOnly, SameSite=Lax, Path=/, Secure เมื่อ CORS_ORIGINS เป็น https), ไม่คืน token ใน body,
    ผิดคืนข้อความเดียว "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง" ทุกกรณี (ทั้ง username/password ผิด)
  - GET /auth/me: ต้องผ่าน current_user ก่อน แล้ว query DB ยืนยันบัญชียังอยู่จริง
  - POST /auth/logout: ลบ cookie
- แก้ response_model ของทุก router (auth/courses/plans/chat/students/feedback) จาก schema เปล่าๆ
  เป็น SuccessEnvelope[schema] เพราะของเดิมใน Prompt 2 ทำให้ /docs โชว์ผิด (ไม่ตรง envelope จริง) —
  บั๊กนี้ไม่เคยแสดงอาการเพราะทุก endpoint ตอนนั้นแค่ raise 501 (exception handler ไม่ผ่าน response_model)
  ตอนนี้ auth คืนค่าจริงแล้วเลยต้องแก้ให้ตรงพร้อมกันทั้งหมดเพื่อความสม่ำเสมอ
- tests/conftest.py: เพิ่ม fixture _db_schema (รัน alembic upgrade head ครั้งเดียวต่อ session),
  db_session (truncate ก่อนทุก test), seeded_demo_student, logged_in_client (ล็อกอินจริงผ่าน HTTP แล้วคืน
  httpx.AsyncClient ที่มี cookie ติดตัว) — ทุก fixture เหล่านี้ noop ถ้าไม่มี TEST_DATABASE_URL
- tests/api/test_auth.py: login สำเร็จ+cookie HttpOnly+ไม่มี token ใน body, รหัสผิด, username ผิด
  (ข้อความเหมือนกัน), /me ไม่มี cookie, token หมดอายุ, token ปลอม, /me สำเร็จ, logout แล้ว session ใช้ไม่ได้อีก
  (ทุกเทสต์ mark @pytest.mark.db)
- src/core/asyncio_compat.py (ensure_selector_event_loop_policy_on_windows): แก้บั๊กที่เจอตอนรันกับ
  Postgres จริงบน Windows — psycopg (async) ต่อ Postgres ไม่ได้ถ้า event loop เป็น ProactorEventLoop
  (default ของ asyncio บน Windows) เรียกใช้ใน tests/conftest.py, migrations/env.py, src/main.py,
  scripts/seed_demo.py ไม่กระทบ Docker/Linux เลย
- scripts/run_dev.py: สคริปต์รัน dev server บน Windows โดยตรง (นอก Docker) เพราะ `uvicorn src.main:app`
  (เรียก CLI ตรง) บน Windows สร้าง ProactorEventLoop ไปแล้วก่อน import แอปเสียอีก (asyncio.run() ของ
  uvicorn เองสร้าง loop ก่อน) ตั้ง policy ในโค้ดแอปเองจึงไม่ทันเวลา ต้องตั้ง policy ก่อนเรียก uvicorn.run()
  เอง — Dockerfile CMD ยังเป็น `uvicorn src.main:app` เหมือนเดิมตาม CLAUDE.md ไม่กระทบเพราะ Linux ไม่ต้อง
  ใช้ workaround นี้ (ยืนยันแล้วว่า login/me/logout ผ่านจริงทั้งผ่าน pytest และผ่าน scripts/run_dev.py จริง)
- แก้บั๊ก hmac.compare_digest ใน POST /auth/login: ของเดิมเทียบ str ตรงๆ ซึ่ง Python raise TypeError
  ถ้า username/password ที่ส่งมามีอักขระนอก ASCII (เช่นพิมพ์ภาษาไทยผิดๆ) ทำให้ได้ INTERNAL_500 แทนที่จะเป็น
  AUTH_401 ปกติ — แก้เป็นเข้ารหัส utf-8 เป็น bytes ก่อนเทียบเสมอ (เจอบั๊กนี้จากการรันเทสต์จริงกับ Postgres
  ไม่ใช่ตอนไม่มี DB เพราะ TestClient ใน tests/unit ไม่เคยส่ง input แบบนี้เข้าไป)

Prompt 5 — Docker + ข้อเสนอสำหรับทีม (ปิด D1):
- entrypoint.sh: alembic upgrade head -> seed (ถ้า SEED_DEMO=true) -> exec uvicorn src.main:app
- Dockerfile: เปลี่ยนจาก CMD ตรงเป็น ENTRYPOINT ["./entrypoint.sh"] (ท้ายสุด entrypoint.sh exec
  uvicorn src.main:app เหมือนเดิม แค่ให้ migrate/seed ก่อนเสมอ) + COPY alembic.ini/migrations/scripts เพิ่ม
- สภาพแวดล้อมนี้ไม่มี docker-compose.yml ที่ root ให้ทดสอบจริงตามข้อ 2 ของ prompt (เป็นไฟล์ของทีมอื่น) —
  ยืนยันแบบเทียบเท่าแทนด้วย `docker build` จริง + `docker run` ผูกกับ container Postgres ที่มีอยู่
  (--link rmutt-test-pg) แล้ว curl /health (200), login (200 + cookie), /me (200) ผ่านครบจากใน container จริง
- handoff/compose.md: ข้อเสนอ env ที่ api_backend ต้องการ + จุดขัดกัน 2 เรื่องเป็นคำถามให้ทีมเลือก (ไม่ตัดสินเอง):
  ROUTER_URL (PLAN.md: http://router:8001) vs ai_router:8100 ที่ prompt บอกว่า compose ใช้อยู่, และ
  CORS_ORIGINS (PLAN.md: localhost:5173) vs web_app:3000 ที่ prompt บอกว่า compose ใช้อยู่ — รวมทั้งผลกระทบ/
  snippet ถ้าจะเปลี่ยน build context เป็น root เพื่อให้ ADAPTER_04/05=inprocess ใช้ได้ใน Docker
- handoff/ci.md: YAML เต็มของ job "api-backend" (postgres:16-alpine service container + ruff + pytest)
  ให้ทีมเอาไปเพิ่มใน .github/workflows/ci.yml เอง — ทดสอบ pattern connection string นี้แล้วว่าใช้ได้จริง
- scripts/test.sh: รัน Postgres ชั่วคราวด้วย `docker run` (ไม่มี compose.yml ให้ใช้) แล้ว ruff+pytest
  คำสั่งเดียว จบแล้ว trap ลบ container ทิ้งอัตโนมัติ — **แก้บั๊กจริงระหว่างทดสอบ**: เดิม hardcode พอร์ต 5432
  ชนกับ Postgres dev container (rmutt-test-pg) ที่รันอยู่แล้ว ทำให้ `docker run` fail ตรงๆ — แก้เป็นให้ Docker
  สุ่มพอร์ตโฮสต์ว่างเอง (`-p 127.0.0.1::5432` แล้วอ่านพอร์ตจริงด้วย `docker port`)
- **แก้บั๊กจริงอีกตัว (สำคัญ)**: คำสั่ง `pytest -q` เปล่าๆ ตามที่ CLAUDE.md เขียนไว้เอง (ไม่ผ่าน `python -m`)
  หา `import src...` ไม่เจอ (ModuleNotFoundError) เพราะ src-layout ไม่ได้ทำเป็น installable package —
  ที่ผ่านมาไม่เคยเจอเพราะทุกครั้งที่รันเทสต์ในเซสชันนี้เรียกผ่าน `python -m pytest` ตลอด ไม่เคยเรียก `pytest`
  เปล่าๆ ตรงๆ แบบที่ CLAUDE.md บอกให้ทำ — แก้ด้วย `pythonpath = ["."]` ใน pyproject.toml
  `[tool.pytest.ini_options]` ยืนยันแล้วว่า `pytest -q` เปล่าๆ ใช้ได้ตรงตาม CLAUDE.md จริง

Prompt 6 — Slice 2: วิชา (D2):
- src/core/redis.py (get_redis(), lru_cache), src/core/cache.py (make_cache_key/cache_get_json/
  cache_set_json — จับ RedisError แล้ว log warning คืน None แทนที่จะ error ตาม PLAN.md)
- src/api/v1/courses.py: implement จริงแทน stub 501 ทั้งสองตัว
  - GET /courses: ต้องล็อกอิน (current_user), เรียก adapter 04, cache 10 นาที (600s) key = hash
    ของ query ทั้งหมด (q/term/day/teacher/cursor/limit) รวม day เป็น Day enum จริงแล้ว (เดิมเป็น str เฉยๆ)
  - GET /courses/{code}/sections: ต้องล็อกอิน, cache แยก key ตาม code+term, ไม่พบ -> NOT_FOUND_404
    (ไม่ cache error เพราะ exception ออกจากฟังก์ชันก่อนถึงบรรทัด cache_set_json)
- tests/api/test_courses.py: สำเร็จ, ไม่ล็อกอิน (401), 04 ล่ม (502 ผ่าน stub adapter ที่ raise
  Upstream502Error ตรงๆ), ไม่พบวิชา (404), cache hit ทั้งสอง endpoint (นับจำนวนครั้งที่ adapter ถูกเรียก
  ผ่าน wrapper class ที่สืบทอดจาก MockCourseCatalog), Redis ล่ม (stub client ที่ raise ConnectionError
  ยืนยันว่ายัง 200 ปกติแค่ cache ใช้ไม่ได้), pagination (next_cursor จริงจาก mock, สอง page ไม่ซ้ำกัน)
- fixtures/courses/list_courses.success.json, sections.success.json: อัปเดตให้ตรง response จริงที่ยิงจาก
  endpoint จริง (ก่อนหน้านี้เป็นตัวอย่างที่เขียนเองตอน Prompt 2 ก่อนมี logic จริง) — error fixtures เดิม
  ตรงกับพฤติกรรมจริงอยู่แล้ว ไม่ต้องแก้

Prompt 7 — Slice 3: แผนการเรียน (D3):
- **แก้ debt จาก Prompt 4 ก่อน**: CLAUDE.md ข้อ 1 ห้าม router แตะ DB ตรงๆ แต่ src/api/v1/auth.py เดิม
  (Prompt 4) query DB ในนั้นเลย — เพิ่ม src/repositories/ (student_repository, plan_repository) และ
  src/services/ (auth_service, plan_service) แล้ว refactor auth.py ให้เรียกผ่าน service ตามชั้นที่ถูกต้อง
  (router -> service -> repository/adapter -> model) plan.py ใหม่ก็เขียนตามชั้นนี้ตั้งแต่แรก
- src/models/plan.py: Plan(student_id FK->students.student_id, term, name, last_validation JSON nullable,
  unique(student_id,term,name)), PlanItem(plan_id FK CASCADE, section_id ไม่มี FK เพราะเป็นของ 04/05, position)
  + migrations/versions/0002_plans.py
- POST /plans/validate: เรียก catalog.get_sections_by_ids() ก่อน (raise NOT_FOUND_404 ถ้ามี id ไม่มีจริง —
  ใช้ adapter 04 pre-check แทนที่จะให้ 06 คืนเป็น conflict แบบเดิม เพราะ prompt ต้องการ 404 จริงไม่ใช่ 200+conflict)
  แล้วเรียก 05.get_context -> 06.validate ตามปกติ (min/max 15 items ให้ pydantic Field คุมอยู่แล้วจาก Prompt 2)
- POST /plans (409 ชื่อซ้ำ), GET /plans (cursor, คำนวณ total_credits โดยเรียก catalog.get_sections_by_ids
  ต่อแผน), GET /plans/{id} (fetch+ownership แยกกัน: ไม่เจอแถว->404, เจอแต่ไม่ใช่เจ้าของ->403), DELETE /plans/{id}
  — last_validation คืน null เสมอ (ดูสมมติฐานด้านล่าง เรื่องไม่เรียก 05/06 ตอน save)
- scripts/seed_demo.py: seed แผนตัวอย่าง "แผนหลัก" เทอม 1/2569 (CPE301-02+GE101-01 ไม่ชนกัน) แบบ idempotent
- tests/conftest.py: TRUNCATE เพิ่ม plan_items,plans, เพิ่ม fixture second_student (มินต์ JWT ตรงไม่ผ่าน
  /login เพราะ login รับได้แค่บัญชีเดโม) ใช้ทดสอบ ownership
- tests/api/test_plans.py (11 เคส, mark @pytest.mark.db): ไม่ชน, C1, C3, section ไม่มีจริง (404), 06 ล่ม (502),
  422 (ว่าง/เกิน 15), บันทึก->list->อ่าน->ลบครบวงจร, ชื่อซ้ำ (409), ownership คนอื่นเข้าถึงไม่ได้ (403 ทั้ง
  GET/DELETE), แผนไม่มีจริง (404)
- fixtures/plans/*: capture จาก response จริงทั้งหมด — **เจอว่า validate.error.json เดิมผิด**: เขียนไว้ตอน
  Prompt 2 เป็นข้อความที่คิดเอง ("ต้องเลือกอย่างน้อย 1 รายวิชา...") แต่พฤติกรรมจริงใช้ pydantic
  Field(min_length=1) ทำให้ error เป็นรูปแบบ RequestValidationError ทั่วไปของ FastAPI/pydantic
  (details.errors เป็น list ของ error object ไม่ใช่ {"field":"section_ids"} แบบที่เดาไว้) แก้ fixture ให้ตรง
  ของจริงแล้ว และเพิ่ม validate.not_found.json ใหม่ (กรณี section ไม่มีจริง ยังไม่เคยมี fixture นี้มาก่อน)
- ยืนยันด้วย curl จริงกับ Postgres ครบ flow ตาม "ส่งมอบ": login -> validate (ไม่ชน) -> POST /plans (save) ->
  GET /plans (เห็นทั้งแผน seed และแผนใหม่) -> GET /plans/{id} (เห็น section เต็มพร้อมชื่อวิชา/เวลา/หน่วยกิตรวม)

Prompt 8 — Slice 4: แชต SSE (D4):
- src/models/chat.py: ChatSession(student_id FK, title, timestamps), ChatMessage(session_id FK CASCADE,
  role, content Text, status, sources JSON, intent nullable ยังไม่มีสัญญาจาก 03 ว่าจะส่งมาไง, latency_ms)
  + migrations/versions/0003_chat.py
- src/core/sse.py: sanitize_event() validate raw event ผ่าน pydantic model ของแต่ละ type ใน schemas/chat.py
  เสมอ (event นอกตาราง 6.2 -> None, tool นอก allowlist -> None) — ใช้ .model_dump() ของ model ที่ validate
  แล้วเป็นตัวส่งออก ทำให้ field แปลกปลอมอย่าง "arguments" หลุดไปเองอัตโนมัติโดยไม่ต้องเขียนโค้ดตัดทิ้งเอง
- src/core/config.py: เพิ่ม TOOL_ALLOWLIST (PLACEHOLDER รอ 03_process.txt จริง) และ CURRENT_TERM (PLACEHOLDER
  เพราะ ChatRequest ไม่มี field term ให้ ต้องยืนยันที่มาจริงกับทีม)
- src/repositories/chat_repository.py, src/services/chat_service.py: resolve_session (null->สร้างใหม่ตั้ง
  title จากข้อความแรก 60 ตัวอักษร, มีเลข->เช็ค owner 403/404), build_history (10 ข้อความล่าสุดที่ complete
  เท่านั้น ผ่าน scrub_text)
- src/api/v1/chat.py — POST /chat ออกแบบเป็น "peek ก่อนเริ่ม stream": เรียก agen.__anext__() รอบแรกเองนอก
  StreamingResponse ด้วย timeout chat_start (15s) ก่อน — ถ้าพัง/timeout ตรงนี้ raise Upstream502Error ปกติ
  (HTTP 502 ธรรมดา ไม่ใช่ SSE) ตรงตาม test list ที่ต้องการ "03 ล่มก่อนเริ่ม (HTTP 502)" แยกจาก "03 ตัดกลางทาง"
  ที่ peek ผ่านไปแล้ว (ได้ event อย่างน้อยหนึ่งอันจริง) ถึงจะเปิด StreamingResponse — 02 ส่ง "session" event
  เองเสมอเป็นอันแรกก่อนเข้า loop (ไม่พึ่ง 03 ว่าจะส่ง session มาถูกหรือไม่), idle timeout 30s/total 120s
  ต่อ event ถัดไป, จบด้วย done->complete, error event จาก 03 เอง->interrupted (forward code/message ของ 03
  ตรงๆ), StopAsyncIteration ไม่มี done->synthesize error event UPSTREAM_502 เอง+interrupted,
  CancelledError (client ตัดการเชื่อมต่อ)->cancelled แล้ว re-raise
- GET /chat/sessions, GET /chat/sessions/{id}/messages: cursor pagination (ใช้ src/core/pagination.py ตัว
  เดียวกับ courses/plans — DRY จากที่เคย copy 2 รอบ), ownership ผ่าน get_owned_session เดียวกับที่ POST /chat ใช้
- tests/sse/test_chat_stream.py (11 เคส, mark @pytest.mark.db) + tests/sse/test_chat_cancel.py (1 เคส,
  เรียก endpoint function ตรงๆ ไม่ผ่าน HTTP เพื่อควบคุม lifecycle ของ generator ได้แม่นยำ แล้ว athrow
  CancelledError จำลอง client disconnect) + tests/unit/test_http_chat_router.py (1 เคส, ทดสอบด้วย
  httpx.MockTransport ส่ง byte stream ที่ตัดกลางตัวอักษรไทย multi-byte พอดี ยืนยันว่า httpx.aiter_lines()
  ที่ HttpChatRouter ใช้อยู่แล้ว decode แบบ incremental ถูกต้อง — เทสต์นี้เป็นจุดเดียวที่ทดสอบผ่าน byte stream
  จริง เพราะ MockChatRouter ที่ใช้ในเทสต์อื่นไม่มีทาง manifest บั๊กประเภทนี้ได้เลย)
- **เจอบั๊กจริงจากการเขียนเทสต์ cancel เอง**: โค้ดเดิม append token เข้า `tokens` list *หลัง* yield
  ทำให้ถ้า client ตัดการเชื่อมต่อพอดีตอน yield (คือหลังจากส่ง token ออกไปให้ client แล้วจริงๆ) ข้อความนั้นจะ
  หายไปจาก content ที่บันทึกเป็น "cancelled" (เพราะโค้ดหลัง yield ไม่ได้รันเมื่อโดน CancelledError ที่จุดนั้น
  พอดี) — ย้าย bookkeeping ทั้งหมดไปก่อน yield แทน แก้แล้วและมีเทสต์คุมไว้
- ปรับ src/adapters/http/chat_router.py ให้รับ `transport` param (เหมือน HttpAdapterClient) เพื่อ inject
  httpx.MockTransport ในเทสต์ได้ ไม่กระทบพฤติกรรมจริง (default None -> ใช้ transport ปกติ)
- fixtures/sse/*.txt: capture จริงจาก POST /chat (ไม่ใช่เขียนมือแบบ Prompt 2) — normal.txt, sources_thai.txt,
  error_mid_stream.txt (03 ส่ง error event ของตัวเอง -> forward ตรงๆ) และ closed_without_done.txt
  (03 เงียบหายไปเฉยๆ -> เห็นว่า 02 synthesize {"code":"UPSTREAM_502",...} เอง) เป็นคนละ error message กันจริง
  ตามที่ Prompt 2 ตั้งใจแยกไว้แต่แรก (ตอนนั้นเขียนมือเดายังไม่มี logic จริง)
- fixtures/chat/sessions.success.json, messages.success.json: capture จริงเช่นกัน (title ตั้งจากข้อความแรก,
  เนื้อหา assistant message เป็น token ต่อกันจริง, sources ตรงกับที่ mock ส่งมา)

Prompt 9 — Slice 5: นักศึกษา, import, auto plan, feedback (D5) — **ปิด backlog endpoint ทั้งหมดแล้ว**:
- src/adapters/interfaces.py: ขยาย StudentContext เพิ่ม program_name/gpax/credits_remaining และเพิ่มเมธอด
  get_transcript() ใน StudentData Protocol เพราะ StudentProfile/TranscriptResponse ต้องการ field ที่ 02
  ไม่เก็บเองเลย (มีแค่ student_id/username/role ใน DB) — อัปเดต Mock/Http/Inprocess ทั้ง 3 ตัวให้ตรงกัน
- GET /students/me/profile: เช็คผ่าน auth_service.get_current_student ก่อน (ยืนยันบัญชียังอยู่ใน DB เหมือน
  /me) แล้วค่อยเรียก 05.get_context() ประกอบเป็น StudentProfile
- GET /students/me/transcript: เรียก 05.get_transcript() ตรงๆ (ไม่แตะ DB ตาม PLAN.md 4.3 ที่ระบุแค่ "05")
- POST /students/me/import: อ่านไฟล์แค่ MAX(2MB)+1 ไบต์ (ไม่ใช่อ่านทั้งไฟล์ก่อนถ้าไม่จำเป็น) เช็คว่าเป็น HTML
  จริงด้วยการหา "<html"/"<!doctype html" ในเนื้อหา (ไม่เชื่อนามสกุล/content-type ที่ client ส่งมา) —
  **ข้อจำกัดที่ต้องบันทึกไว้**: FastAPI/Starlette parse multipart body ทั้งก้อนไว้ในหน่วยความจำ/ไฟล์ชั่วคราว
  ก่อนโค้ดเราจะได้ควบคุมอะไรเลย ("ตรวจระหว่างอ่าน ไม่อ่านทั้งไฟล์ก่อน" ตามตัวอักษรทำไม่ได้เต็มร้อยด้วย
  UploadFile มาตรฐานของ FastAPI ต้องเขียน multipart parser เองระดับ ASGI ถึงจะทำได้จริง ถือว่าเกินขอบเขต
  ของ slice นี้ — สิ่งที่ทำได้คือจำกัดไม่ให้โค้ดเราเองถือ bytes เกินจำเป็นหลัง Starlette parse เสร็จแล้ว)
- POST /plans/auto: ดึง student_preferences จาก DB ของ 02 เอง (ไม่ใช้ payload.preferences ที่ client ส่งมา
  เลยตามที่ prompt สั่ง) เรียก 06.generate() แล้ววนเรียก 07.explain_plan() ทีละแผน — 07 ล่ม (Upstream502Error)
  -> จับเฉพาะ exception นี้ ไม่ catch Exception กว้างๆ ใส่ explanation=null + warning ต่อแผนนั้น ไม่ล้มทั้ง
  request (แผนอื่นที่ยัง explain สำเร็จก็ยังได้ explanation ปกติ)
- GET /plans/{id}/explain: fetch+ownership ผ่าน helper เดียวกับ get_plan_detail/delete_plan (รีแฟกเตอร์เป็น
  _get_owned_plan ใช้ร่วมกัน 3 endpoint) แล้วเรียก 07 ตรงๆ ไม่มี graceful degradation (ต่างจาก auto เพราะ
  prompt ไม่ได้บอกให้ผ่อนปรนตรงนี้ — ล่มคือ 502 ปกติ)
- model Feedback + migration 0004, feedback_service ตรวจ ownership ตาม target_type: "plan"/"explanation"
  เช็คกับตาราง plans (ยังไม่มีที่เก็บ explanation แยก เลยผูก "explanation" กับ plan_id เดียวกัน),
  "chat_message" เช็คกับ chat_messages -> chat_sessions.student_id
- src/core/log_queue.py: deque ในหน่วยความจำ max 1000, flush ทุก 2 วินาทีผ่าน adapter 08 (get_log_sink()),
  เต็ม/ส่งไม่สำเร็จ -> นับ log_dropped_total ทั้งคู่ (ไม่ใช่แค่เต็มอย่างเดียว), shutdown flush ภายใน 3 วินาที
  ผ่าน lifespan ใน main.py — enqueue() เรียกจาก validate/auto/chat/feedback ด้วย payload ที่มีแค่ id_hash
  (ไม่มี student_id ดิบ ไม่มีเนื้อข้อความ) แล้วผ่าน mask_payload() อีกชั้นเป็นการป้องกันซ้อน
- **ตัดสินใจ**: feedback "ส่งสำเนา 08" ผ่าน log_queue (send_batch) เหมือน validate/auto/chat ทั้งที่ LogSink
  interface มี send_feedback() แยกไว้ตั้งแต่ Prompt 3 — เมธอดนั้นเลยยังไม่ถูกเรียกใช้จริงที่ไหนเลยในโค้ดทั้งหมด
- tests: tests/api/test_students.py (11 เคส), tests/api/test_plans.py เพิ่ม auto/explain (7 เคสใหม่),
  tests/api/test_feedback.py (6 เคส), tests/unit/test_log_queue.py (8 เคส: mask ก่อนเก็บ, เต็มนับ dropped,
  flush สำเร็จ/ล้มเหลว, background task, shutdown flush), tests/unit/test_inprocess_student_data_integration.py
  เพิ่มเคส parse fixtures/import/sample_sanitized.html ให้ตรง expected.json (skip เพราะ 05 ยังไม่มี เหมือนเคสเดิม)
- **แก้บั๊กจริงจากผลข้างเคียง**: tests/unit/test_errors.py 2 เคสเดิมใช้ /plans/auto เป็น "endpoint ที่ยังไม่
  implement" (พังมาแล้วรอบหนึ่งตอน Prompt 7 ตอนใช้ /plans/{id} แล้วก็พังอีกรอบตอนนี้เพราะ auto implement แล้ว)
  คราวนี้แก้ให้ถูกทางถาวร: สร้างแอปทดสอบแยกต่างหากที่ผูก exception handler/middleware ตัวจริงจาก src.main
  เข้ากับ route ปลอมของตัวเอง ไม่ต้องพึ่ง business endpoint ใดๆ ของแอปจริงอีกต่อไป (กันไม่ให้บั๊กรูปแบบนี้
  เกิดซ้ำเป็นรอบที่ 3 ในอนาคต)
- fixtures/import/sample_sanitized.html + expected.json: สร้างขึ้นเองทั้งคู่ (ข้อมูลสังเคราะห์ล้วนๆ) เพราะไม่มี
  ไฟล์ตัวอย่างจริงจาก 05 — fixtures/plans/auto.success.json, auto.explainer_down.json (ใหม่), explain.success.json
  capture จริงจาก endpoint แล้ว

สมมติฐาน/จุดที่ยังไม่ได้ยืนยันกับทีม (ต้องแจ้งทีมก่อนใช้งานจริง):
- PlanValidateResponse (conflicts[]/warnings[]/summary) และกติกา C1/C3/C4/C6 ใน MockPlanEngine
  ออกแบบเองคร่าวๆ เพราะไม่มีไฟล์ 06_schedule_conflict_engine/03_process.txt ให้ยึด
- URL/path ของ http adapter ทุกโมดูล (COURSE_CATALOG_URL, STUDENT_DATA_URL, PLAN_ENGINE_URL,
  EXPLAINER_URL, LOG_SINK_URL และ PATH_* ในแต่ละไฟล์ src/adapters/http/*.py) เป็น PLACEHOLDER ล้วนๆ
- MODULE_04_DIR="04_course_data" เป็นชื่อโฟลเดอร์ที่เดาไว้ (ยังไม่รู้ชื่อจริงของโมดูล 04)
- โครงสร้าง field ของ plan_input จาก mod05.degree_plan.build_plan_input ใน InprocessStudentData
  เป็นการเดา (courses/retake_required/credits_remaining/warnings) ต้องแก้เมื่อ 05 มีโค้ดจริง
- src/models/student.py (students, student_preferences): field เดาเองล้วนๆ เพราะไม่มีไฟล์
  00_docs/05_data_model.md ในสภาพแวดล้อมนี้ — ต้องเทียบกับของจริงก่อนใช้งาน อาจต้องแก้ migration
  0001_initial.py ถ้า field ไม่ตรง (มี migration 0002 ต่อแล้ว ถ้าจะแก้ 0001 ทำได้เพราะยังไม่มีใครใช้จริง)
- last_validation ของ Plan เป็น null เสมอ เพราะตัดสินใจว่า POST /plans (save) จะไม่เรียก adapter 05/06 เอง
  ตาม PLAN.md 4.3 ที่เขียนว่า POST/GET /plans เรียกไปที่ "DB" เท่านั้น (ต่างจาก POST /plans/validate ที่ระบุ
  "05 -> 06" ชัดเจน) — ถ้าทีมต้องการให้ save พร้อมบันทึกผลตรวจล่าสุดด้วย (เรียก validate ซ้ำตอน save) ต้อง
  ยืนยันก่อน เพราะขัดกับที่ตารางเขียนไว้
- TOOL_ALLOWLIST ("search_knowledge,search_courses,check_schedule_conflict,generate_plan") เป็นชื่อ tool ที่
  เดาเอง เพราะไม่มีไฟล์ 03_ai_router_agent/03_process.txt (INTENT -> TOOL MAP) ในสภาพแวดล้อมนี้เลย
- CURRENT_TERM ("1/2569" ค่าเดียวกับ mock data) ใช้เป็น `term` ใน EnrichedChatRequest ที่ส่งให้ 03 เพราะ
  ChatRequest (จากหน้าเว็บ) ไม่มี field term ให้เลย — ต้องยืนยันกับทีมว่าจริงๆ ควรมาจากไหน (เทอมปัจจุบันของ
  ระบบ/เทอมของแผนล่าสุดของนักศึกษา/ให้ 01 ส่งมาเพิ่ม) ตอนนี้ทุก session ใช้ค่าคงที่เดียวกันหมด
- intent column ใน chat_messages ยังไม่มีการ populate เลย เพราะ event ตาราง 6.2 ไม่มี field นี้ให้ 02 รับมา
  จาก 03 — เก็บ column ไว้เผื่ออนาคตเฉยๆ ตามที่ prompt สั่งให้มี แต่ไม่มีสัญญาว่าจะได้ค่ามายังไง
- HttpChatRouter (ADAPTER 03 จริง) ยังไม่เคยทดสอบกับ 03 ตัวจริงเลย (ไม่มีให้ทดสอบ) ทดสอบแค่ MockChatRouter
  ผ่าน dependency override กับ httpx.MockTransport ระดับ byte stream สำหรับเคส UTF-8 เท่านั้น — logic ของ
  02 (filter/timeout/error-handling) ยืนยันครบผ่าน mock แต่ยังไม่เคยเห็น response จริงจาก 03 มาก่อน
- StudentContext ขยาย field เพิ่ม (program_name/gpax/credits_remaining) และ StudentData.get_transcript()
  เป็นเมธอดใหม่ที่ 02 กำหนดเอง — 05 ต้องคืนค่าตามนี้เป๊ะๆ ยังไม่เคยยืนยันกับทีม 05 ว่ารับได้ไหม
- POST /students/me/import "ตรวจระหว่างอ่าน ไม่อ่านทั้งไฟล์ก่อน" ทำได้ไม่เต็มร้อยตามตัวอักษร เพราะ
  FastAPI/Starlette parse multipart body ทั้งก้อนก่อนโค้ดเราจะควบคุมอะไรได้ (ต้องเขียน ASGI multipart parser
  เองถึงจะทำได้เต็มรูปแบบ — เกินขอบเขต slice นี้) ทำได้แค่ไม่ถือ bytes เกินจำเป็นในโค้ดของเราเอง
- feedback ของ target_type="explanation" ผูก ownership check กับตาราง plans โดยตรง (เดาว่า target_id คือ
  plan_id เพราะไม่มีที่เก็บ explanation แยกเป็น entity ของตัวเอง) ต้องยืนยันกับทีมว่าตีความถูกไหม
- LogSink.send_feedback() (มีมาตั้งแต่ Prompt 3) ยังไม่ถูกเรียกใช้จริงที่ไหนเลย เพราะ feedback ไป log_queue
  (send_batch) แทนตามที่ Prompt 9 สั่งให้ feedback ใช้ log_queue เหมือน validate/auto/chat

ตรวจสอบแล้ว (ล่าสุด, กับ Postgres จริงใน docker container ชื่อ rmutt-test-pg):
- pytest -q -> 163 passed, 2 skipped (skip เหลือแค่ 2 ตัวที่ต้องมี 05_data_integration จริง), ruff check . ->
  ผ่านหมด (ทั้งแบบ `python -m pytest` และแบบ `pytest` เปล่าๆ ตาม CLAUDE.md)
- alembic upgrade head ผ่าน 0001->0002->0003->0004 เรียบร้อย (ตรวจด้วย `alembic history`/`alembic current`)
- ยืนยันด้วย server จริง (scripts/run_dev.py + curl/httpx): login -> GET /plans เห็นแผน seed "แผนหลัก" ->
  GET /plans/{id} เห็น section เต็ม (ชื่อวิชา/อาจารย์/เวลา/ห้อง) พร้อมหน่วยกิตรวมถูกต้อง (6 = 3+3)
- smoke test ครบทั้ง D5 กับ server จริง+Postgres จริงรวดเดียว: login -> profile -> transcript -> import ->
  auto plan -> save plan -> explain -> feedback ผ่านหมดทุกขั้นตอน (200 ทุกตัว)
- ตรวจ OpenAPI schema จริง: 18 endpoint ครบ ไม่มีตัวไหนเหลือ NotImplemented501Error ในโค้ดแล้ว (grep ยืนยัน)
- POST /chat capture จริงผ่าน ASGITransport (ไม่ผ่าน HTTP จริงเพราะ 03 ยังไม่มีให้ต่อ) ครบ 4 สถานการณ์
  (ปกติ, sources ไทย, error จาก 03 เอง, ปิดไม่มี done) ลง fixtures/sse/*.txt และ GET /chat/sessions,
  GET /chat/sessions/{id}/messages capture จริงลง fixtures/chat/*.json แล้ว
- docker run postgres:16-alpine -> alembic upgrade head (ผ่าน CLI ตรงๆ ไม่ใช่แค่ผ่าน pytest fixture) ->
  scripts/seed_demo.py รันสำเร็จและ idempotent (รันซ้ำไม่พัง) -> boot จริงด้วย scripts/run_dev.py ->
  curl/httpx login (200, ได้ cookie HttpOnly, ไม่มี token ใน body) -> me (200, เห็นข้อมูลถูกต้อง) ->
  logout (200) -> me หลัง logout (401) ครบทุกขั้นตอนจริง ไม่ใช่แค่ unit test
- `docker build .` จริง -> `docker run` (ผูกกับ rmutt-test-pg) -> curl /health (200), login (200 + cookie),
  /me (200) ผ่านครบจาก container จริงที่ build จาก Dockerfile จริง (ไม่ใช่แค่รัน uvicorn ตรงนอก Docker)
- scripts/test.sh รันจริงจบแล้ว container ลบตัวเองอัตโนมัติ (ยืนยันด้วย docker ps -a ว่าไม่เหลือค้าง)
- /docs ตรวจแล้วว่า POST /auth/login response schema เป็น SuccessEnvelope_LoginResponse_ ถูกต้อง

D1 จบสมบูรณ์แล้วตาม PLAN.md หัวข้อ 8 — เทียบกับหัวข้อ 11 (สิ่งที่ 02 ส่งให้ทีม ภายใน D1): ตอนนั้นขาดแค่
"allowlist ของ tool" ซึ่งเป็นงานของ Prompt 8/D4 อยู่แล้ว (ไม่ใช่ D1) — ตอนนี้ Prompt 8 เสร็จแล้ว มี
TOOL_ALLOWLIST ครบด้วย ถือว่าส่งครบทุกข้อในหัวข้อ 11 แล้ว

04/05 (โมดูลของเพื่อน) ยังไม่มีโค้ดใน GitHub เลย — เมื่อเพื่อนเริ่มทำแล้ว ให้ตั้ง MODULES_ROOT ชี้ไปที่
โฟลเดอร์ที่วางโมดูลพวกนี้ (default คือ parent ของ 02_api_backend) แล้วรัน pytest ใหม่ เทสต์ inprocess
ที่ skip อยู่จะรันเองทันที ไม่ต้องแก้โค้ดเทสต์

Prompt 10 — Slice 6: ความเรียบร้อย + เอกสาร (D6):
- rate limit: **เขียนรอบแรกเป็น raw ASGI middleware (BaseHTTPMiddleware) แล้วเจอบั๊กจริงทันที** —
  middleware เรียก get_redis() ตรง (lru_cache) ไม่ผ่าน FastAPI DI เลย ทำให้ app.dependency_overrides
  ที่ทุก test พึ่งอยู่ (override เป็น fakeredis) ไม่มีผลกับ middleware ผลคือทั้ง suite พยายามต่อ Redis จริง
  ที่ไม่มีอยู่จนค้าง (จากเดิม ~5 วิ กลายเป็น timeout) แก้ถาวรด้วยการเขียนใหม่ทั้งหมดเป็น FastAPI dependency
  ธรรมดา (`rate_limit(request, redis=Depends(get_redis))`) แล้วผูกที่ระดับ router ทั้งชุดด้วย
  `app.include_router(api_router, prefix="/api/v1", dependencies=[Depends(rate_limit)])` แทน — บทเรียน:
  cross-cutting concern ที่ต้อง testable ต้องเป็น Depends() เสมอ ห้ามเป็น raw middleware ที่เรียก singleton ตรง
- เพิ่ม autouse fixture `_default_fake_redis` ใน tests/conftest.py ให้ทุก test ต่อ fakeredis แทน Redis จริง
  โดยอัตโนมัติ (เดิมมีแค่บาง test ที่ override เอง) เพราะตอนนี้ rate_limit เป็น dependency ที่ทำงานกับทุก
  request ใต้ /api/v1 แล้ว ไม่ใช่แค่ endpoint ที่ทดสอบ cache เหมือนก่อน — ต้อง override ให้ครบทุก test
- rate limit fixed window ผ่าน Redis INCR+EXPIRE: ทั่วไป 60/นาที ต่อ student_id (หรือ IP ถ้ายังไม่ login),
  /chat 10/นาที ต่อ student_id, /auth/login 5/นาที ต่อ IP — เกิน -> RATE_429 + header Retry-After,
  Redis ล่ม (RedisError) -> fail open (ปล่อยผ่านไม่ error) + log warning เท่านั้น
- GET /ready: เรียก check_readiness(settings, engine, redis) จาก src/services/readiness_service.py ตรงๆ
  (ไม่ผ่าน Depends() เหมือน endpoint อื่น) — **ตั้งใจ** เพราะ readiness ต้องสะท้อนสถานะ infra จริงเสมอ
  ไม่ควร override ได้ในโหมด test/demo; ผลคือ /ready เองไม่มี HTTP-level test (จะ flaky ตามสภาพแวดล้อมจริง)
  แต่ทดสอบ logic ล้วนๆ ของ check_database/check_redis/check_http_module/check_readiness ผ่าน fake
  engine/redis + httpx.MockTransport ใน tests/unit/test_readiness_service.py แทน (9 เคส) — เพิ่ม parameter
  `transport` ให้ check_http_module() แบบเดียวกับ HttpAdapterClient/HttpChatRouter เพื่อทดสอบได้โดยไม่ต่อ
  เน็ตจริง Postgres/Redis เช็คเสมอ, โมดูล 04-08 เช็คเฉพาะตัวที่ตั้ง ADAPTER=http, 03 เช็คเสมอ
- GET /metrics: ต่อ prometheus-fastapi-instrumentator (Instrumentator().instrument(app).expose(...))
  รวม log_dropped_total (Gauge จาก src/core/log_queue.py) — ทดสอบจริงว่า /metrics คืน 200 และมีทั้งสอง
  metric นี้จริงใน tests/api/test_meta_endpoints.py (รวม /health และยืนยันว่า /health,/metrics ไม่มี prefix
  /api/v1 และไม่ผ่าน rate_limit)
- requirements.lock: **ไม่ได้ pip freeze จาก .venv dev ตรงๆ** เพราะจะติด pytest/ruff/fakeredis ปนเข้าไปด้วย
  (เป็น dev-only ไม่ควรอยู่ใน production image) สร้าง venv ชั่วคราวแยกต่างหาก ติดตั้งเฉพาะ requirements.txt
  แล้ว freeze จาก venv นั้นแทน ได้ 41 บรรทัด (prod เท่านั้น) — แก้ Dockerfile ให้ COPY+pip install จาก
  requirements.lock แทน requirements.txt ตรงๆ แล้ว `docker build` ยืนยันสำเร็จจริงด้วย lock file นี้
- ไล่ตรวจ PLAN.md §9 (ทุก endpoint ≥3 เคส + ownership) เจอช่องว่างจริง 3 จุด เติมให้ครบ:
  1) GET /courses/{code}/sections มีแค่ 2 เคส (not_found, cache_hit) เพิ่ม success + without-login-401 +
     upstream-502 ให้ครบ
  2) GET /chat/sessions และ GET /chat/sessions/{id}/messages ไม่มี test เฉพาะทางเลย (ถูกเรียกผ่านๆ ใน test
     อื่นเท่านั้น) เพิ่ม without-login-401, empty-list, ownership (เห็นแค่ของตัวเอง), 404 (session ไม่มีจริง),
     403 (session เป็นของคนอื่น) รวม 7 เคสใหม่ใน tests/sse/test_chat_stream.py
  3) POST /auth/logout มีแค่ 1 เคส เพิ่ม envelope ok:true + logout ตอนยังไม่ login ก็ต้องได้ 200 เหมือนกัน
- scripts/smoke.sh: จำลอง clean-clone จริง (ไม่มี docker-compose.yml ที่ root ให้ใช้ในสภาพแวดล้อมนี้ เหมือน
  ปัญหาเดียวกับ scripts/test.sh ตอน Prompt 5) ใช้ `docker network create` ต่อ Postgres+Redis+api container
  จริงเข้าด้วยกันแทน แล้ว curl ครบ login->courses->validate->save->chat — **รันผ่านจริงแล้ว** (build image
  จริง, migrate จริงผ่าน entrypoint.sh, seed จริง, ทุก step 200 ยกเว้น chat ที่ตั้งใจให้ได้ UPSTREAM_502
  เพราะยังไม่มี router 03 จริงให้ต่อในสภาพแวดล้อมนี้ — สคริปต์เช็คว่าเป็น 502 envelope ที่ถูกต้อง ไม่ใช่ปล่อยผ่าน
  เฉยๆ) cleanup container/network/image อัตโนมัติผ่าน trap EXIT ยืนยันด้วย `docker ps -a` ว่าไม่เหลือค้าง
- เอกสาร: README.md ใหม่ (วิธีรัน dev/Docker, env vars หลัก, curl ตัวอย่างครบ flow, โครงสร้างโค้ด, ข้อจำกัด
  ที่ทีมต้องรู้) · handoff/api-spec.md สร้างจาก app.openapi() จริง (export handoff/openapi.json ด้วย
  ผ่าน `python -c "...app.openapi()..."`) · อัปเดต 01_env.txt/02_step.txt/03_process.txt ให้ตรงโค้ดจริง
  ทั้งหมด (ของเดิมยังอ้าง app/ และชื่อ env รุ่นเก่าอย่าง AI_ROUTER_URL/SCHEDULE_ENGINE_URL/COURSE_DATA_URL
  ที่ไม่ตรงกับ .env.example จริงเลย)

ตรวจสอบแล้ว (Prompt 10, กับ Postgres จริงใน docker container ชื่อ rmutt-test-pg):
- pytest -q -> 190 passed, 2 skipped (จากเดิม 163 ก่อน Prompt 10 — เพิ่ม 27 เทสต์ใหม่: rate_limit(4),
  readiness_service(9), meta_endpoints(3), sections gap(3), chat sessions/messages gap(7), logout gap(2)),
  ruff check . -> ผ่านหมด ทั้งแบบมี TEST_DATABASE_URL (190 passed) และไม่มี (132 passed, 60 skipped)
- docker build . สำเร็จจริงด้วย requirements.lock (ไม่ใช่ requirements.txt ตรงๆ อีกต่อไป)
- scripts/smoke.sh รันผ่านจริงครบ (build image + Postgres/Redis จริง + curl 5 ขั้นตอน) cleanup อัตโนมัติ
  ไม่เหลือ container/network/image ค้าง
- GET /metrics ตรวจจริงว่ามี log_dropped_total และ metric มาตรฐานของ instrumentator อยู่จริงในผลลัพธ์

ข้อสังเกตระหว่างทำ (ไม่ใช่บั๊ก แต่ควรรู้): เจอ background test run ค้างเก่าที่ล้มเหลว (FK violation +
Redis fail-open log จำนวนมาก ใช้เวลา 405 วิ) ระหว่างทำ Prompt 10 — ตรวจแล้วเป็นผลลัพธ์ค้างจากรอบทดสอบ
ก่อนจะแก้บั๊ก rate-limit middleware (ข้อ "rate limit" ด้านบน) ไม่ใช่สถานะปัจจุบัน รันซ้ำสดๆ แล้วได้ผลสะอาด
(176/179/190 passed ตามลำดับที่ทยอยเพิ่ม test) ยืนยันว่าไม่ใช่บั๊กที่หลงเหลืออยู่จริง

D6 (Slice 6) จบแล้ว หมายเหตุ: 00_docs/04_team_roles.md (อ้างถึงใน Prompt 10 สำหรับ "Definition of Done")
ไม่มีอยู่จริงในสภาพแวดล้อมนี้ (ไม่มีโฟลเดอร์ 00_docs เลย) เลยตอบคำถามปิดท้ายของ Prompt 10 โดยเทียบกับ
checklist 5 ข้อใน PLAN.md §8 D6 แทน — ถ้าทีมมีไฟล์ 04_team_roles.md จริง ควรเทียบซ้ำอีกที

Prompt 11 — ตรวจรอบสุดท้าย (D7):
- เทียบ PLAN.md §4.3 กับ OpenAPI จริง (export จาก app.openapi()): ครบทั้ง 18 endpoint + health/ready/metrics
  ตรงกันทุกตัว grep `NotImplemented501Error`/`NOT_IMPLEMENTED_501` ในโค้ดเจอแค่ definition ของ error class
  เอง ไม่มี router ไหนเรียกใช้จริงแล้ว
- ไล่ checkbox PLAN.md §8 ทุกข้อ: D1-D6 ติ๊กครบหมดแล้วตั้งแต่ก่อนหน้า (D5 เหลือ 1 ข้อไม่ติ๊กโดยตั้งใจ —
  "เปลี่ยน adapter จาก mock เป็นของจริง" เพราะ 04-08 ยังไม่มีโค้ดจริงให้เปลี่ยนไปใช้) เพิ่ม D7 ติ๊กครบ 2 ข้อ
- ตรวจความปลอดภัย: grep logger.*(info|warning|error) ทุกจุดในโค้ด — มีแค่ count/scope/cache-key(จาก
  course search params ไม่ใช่ PII)/error_type เท่านั้น ไม่มี student_id/ชื่อ/เนื้อแชตหลุด log เลย · ยืนยัน
  id_hash (ไม่ใช่ student_id ดิบ) เท่านั้นที่ส่งให้ 03 + scrub_text() ทั้งข้อความใหม่และ history + mask_payload()
  ก่อนเข้า log_queue เสมอ · cookie session มี HttpOnly/SameSite=Lax/Path=/ ครบ (Secure ผูกกับ CORS_ORIGINS
  startswith https — เจอ edge case เล็กน้อยถ้ามีหลาย origin คั่น comma ตัวแรกไม่ใช่ https บันทึกไว้เป็น known
  issue ใน HANDOFF.md ไม่ได้แก้เพราะยังไม่ใช่บั๊กที่กระทบการใช้งานจริงตอนนี้ dev ใช้ origin เดียวเสมอ) ·
  CORS_ORIGINS มี field_validator บังคับห้ามเป็น "*" อยู่แล้ว (src/core/config.py) · grep หา .env จริง/secret
  hardcode/รหัส นศ. รูปแบบจริง (`1xxxxxxxxxxx-x`) นอก tests/fixtures — ไม่พบสักจุดเดียว
- **พบช่องโหว่จริง 1 จุดและแก้แล้ว**: ไม่มี `.gitignore` เลยตั้งแต่ต้นโปรเจกต์ (เสี่ยง commit `.venv/`,
  `__pycache__/`, `.env` จริงเข้า repo ตอน `git init` ครั้งแรกที่ยังไม่เกิดขึ้น) เพิ่ม `.gitignore` ครอบคลุม
  `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.env`, `*.egg-info/`
- รัน pytest -q (190 passed, 2 skipped), ruff check . (ผ่านหมด), scripts/smoke.sh (ผ่านครบ build+
  Postgres+Redis+api จริง+curl 5 ขั้นตอน) ซ้ำอีกรอบหลังแก้ .gitignore ยืนยันไม่มีอะไรพัง
- **"git diff main --stat" ทำไม่ได้จริง** เพราะไม่มี git repository ในสภาพแวดล้อมนี้เลย (`git status` ->
  "not a git repository") ใช้วิธีตรวจแทนคือ list โฟลเดอร์ `E:\ML` ทั้งหมด ยืนยันว่ามีแค่โฟลเดอร์
  `02_api_backend/` อยู่ข้างในเท่านั้น (ไม่มีไฟล์/โฟลเดอร์อื่นถูกสร้างเลยตลอดทั้ง 11 prompt) — commit
  "[02] fix: ..." และ "[02] เพิ่ม HANDOFF.md" ตามที่ prompt สั่งก็ข้ามด้วยเหตุผลเดียวกัน (ผู้ใช้บอกไว้ตั้งแต่
  ต้นโปรเจกต์แล้วว่า "ยังไม่ต้อง git — แค่สร้างไฟล์โค้ดไปก่อน") ทีมที่รับงานต่อต้อง `git init`
  (หรือ copy เข้า repo จริง) เอง แล้วค่อย commit ตามข้อความที่ prompts กำหนดไว้
- เขียน handoff/HANDOFF.md: ตารางสถานะทุก endpoint, สรุปว่า 03-08 ทุกตัวยังเป็น mock ล้วนๆ ไม่เคยต่อของ
  จริงเลยสักตัว (เหตุผลแยกตามโมดูล), known issues 12 ข้อ (รวม contract ที่เป็นการเดาทั้งหมด, field ที่ 02
  กำหนดเองที่ 05 ต้องยืนยัน, edge case ของ Secure cookie flag, ไม่มี git repo), ผลตรวจความปลอดภัยรอบสุดท้าย,
  และ curl script สาธิต flow เต็มด้วยบัญชี admin/admin1234 ทีละขั้นตอน

ยังไม่ทำ: ไม่มี — **ครบทั้ง 11 prompt แล้ว (D1-D7)** งานที่เหลือทั้งหมดอยู่นอกขอบเขตของ 02 เอง คือ:
รอทีม 04-08 มีโค้ดจริงแล้วสลับ adapter, รอทีม 03 มี router จริงแล้วต่อ HTTP จริง, ทีมกลาง git init +
push + เปิด PR (ทำไม่ได้ในสภาพแวดล้อมนี้เพราะไม่มี git repo และผู้ใช้ยังไม่ได้ขอให้ทำ)

ทดสอบซ้ำได้ด้วยตัวเองบนเครื่องนี้ (ถ้า container rmutt-test-pg ยังรันอยู่ ไม่ต้องสร้างใหม่):
  export TEST_DATABASE_URL=postgresql+psycopg://rmutt:change_me_please@localhost:5432/rmutt_test
  cd 02_api_backend && pytest -q
  # รัน dev server จริงบน Windows (ไม่ผ่าน Docker): python -m scripts.run_dev
  # รัน lint+test all-in-one แบบไม่ต้องมี container ของตัวเองมาก่อน: sh scripts/test.sh
  # build+run เป็น container จริง: docker build -t rmutt-api-backend:test .
  # smoke test แบบ clean-clone เต็มรูปแบบ (build+Postgres+Redis+api+curl ครบ flow): sh scripts/smoke.sh
```

---

## ย้ายเข้า git repo ของทีม (ProJ-RMUTT-Planner) — พบ integration จริงครั้งแรกกับ 05

ย้ายงานจากเครื่อง dev แยกต่างหากเข้า repo ทีมจริง (`Onpreyaq5/Nuthaluek-CPE-LLM-`) ผ่าน robocopy ตาม
CONTRIBUTING.md — ตอน robocopy เสร็จแล้วรัน `pytest -q` ซ้ำในตำแหน่งใหม่ **เจอ 2 เทสต์ failed ที่ไม่เคย
failed มาก่อนบนเครื่อง dev เดิม**:

- **สาเหตุ**: `tests/unit/test_inprocess_student_data_integration.py` ถูกออกแบบให้ `skipif` เมื่อไม่มี
  โฟลเดอร์ `05_data_integration` — บนเครื่อง dev เดิมไม่มีโฟลเดอร์นี้เลยเลย skip ทุกครั้ง แต่ **ใน repo ทีมจริง
  เพื่อนเจ้าของโมดูล 05 เขียนโค้ดจริงไปแล้ว** (`graduate_check.py` parser หน้า "ตรวจสอบจบ", `degree_plan.py`
  `build_plan_input()`) เงื่อนไข skip เลยไม่ทำงาน เทสต์รันจริงแล้วเจอบั๊กจริงของเราเอง 2 ชั้น:
  1. **บั๊กเทคนิค** ใน `src/adapters/inprocess/student_data.py`: `self._mod.graduate_check` ใช้ไม่ได้เพราะ
     `load_module_package()` โหลดแค่แพ็กเกจหลัก ไม่ import submodule ให้อัตโนมัติ (Python ไม่ทำแบบนั้นเอง)
     → `AttributeError` แก้ด้วยการ `importlib.import_module("mod05.graduate_check")` /
     `importlib.import_module("mod05.degree_plan")` ตรงๆ ก่อนใช้งาน
  2. **บั๊ก contract ที่ลึกกว่า**: field ที่เดาไว้ตอน Prompt 3/9 (`courses`, `retake_required`,
     `credits_remaining`, `warnings` บน `plan_input`) **ไม่ตรงกับของจริงสักตัว** — ของจริงจาก
     `degree_plan.build_plan_input()` คือ `DegreePlanInput(student_id, term, min_total_credits,
     passed_credits, remaining_total, categories, candidates)` แก้ mapping ใหม่ตามของจริง:
     `imported_courses = len(audit.all_courses())`, `retake_required` = รหัสวิชาจาก
     `audit.failed_courses()`, `credits_remaining = plan_input.remaining_total`, `warnings = []`
     (05 ไม่มีแนวคิด warning ตรงๆ — ปล่อยว่างแทนเดาเนื้อหาเอง)
- **ผลหลังแก้**: `test_inprocess_student_data_parses_real_fixture` (ใช้ fixture จริงของ 05) **ผ่านจริง** —
  เป็นการ integration กับของจริงครั้งแรกของทั้งโปรเจกต์ (03/04/06/07/08 ยังไม่มีให้ต่อจริงเลยจนถึงตอนนี้)
  แต่ `test_inprocess_import_matches_expected_json` ยัง fail เพราะ `fixtures/import/sample_sanitized.html`
  ของเราเอง (แต่งขึ้นก่อนมีของจริง เป็นรูปแบบ "รายงานผลการศึกษา" ทั่วไป) ไม่ตรงกับรูปแบบหน้า "ตรวจสอบจบ" จริงที่
  `parse_graduate_check()` ต้องการ (regex/table structure เฉพาะเจาะจงมาก) parse ได้ผลว่างเสมอ — **ตัดสินใจ
  mark เป็น `skip` แทนที่จะพยายามแต่ง fixture ปลอมให้ตรงหน้าจริงของระบบทะเบียน** (เสี่ยงเดาโครงสร้างผิดมากกว่า
  จะได้ประโยชน์ ในเมื่อมี fixture จริงของ 05 ยืนยัน integration ได้แล้วผ่าน test อีกตัว) ต้องขอตัวอย่างหน้า
  "ตรวจสอบจบ" จริงที่ลบข้อมูลระบุตัวตนแล้วจากทีม 05 มาแทนไฟล์นี้ถ้าจะทดสอบ end-to-end กับข้อมูลของเราเองต่อ
- **บันทึกไว้ใน `handoff/HANDOFF.md`** known issue #2 (อัปเดตแล้ว) และตารางสถานะ endpoint `/import`
  ให้แยกจาก `/profile`+`/transcript` เพราะตอนนี้ต่อ 05 จริงสำเร็จแล้ว (แค่ field mapping ยังไม่ยืนยัน)
- **ผลตรวจสุดท้ายหลังแก้**: `pytest -q` กับ Postgres จริง (ผ่าน `scripts/test.sh`) → **191 passed, 1 skipped**
  (ดีขึ้นจากเดิม 190 passed, 2 skipped เพราะเทสต์ integration จริงตัวหนึ่งเปลี่ยนจาก skip เป็น pass จริง)
  `ruff check .` ผ่านหมด, `python -m compileall -q 0*/src` (ตามที่ CI ของทีมใช้จริง ตรวจสอบจาก
  `.github/workflows/ci.yml`) ผ่านหมดทุกโมดูลรวม 05/04 ที่มีโค้ดจริงแล้วด้วย

**ข้อสังเกตเพิ่มเติมเกี่ยวกับ CI ของทีม** (`.github/workflows/ci.yml`, อ่านอย่างเดียวไม่ได้แก้): job
`python-tests` (matrix) ตอนนี้มีแค่ `04_course_data_services`, `05_data_integration` — **ยังไม่มี
`02_api_backend`** ในรายการ ถ้าจะเพิ่มทีหลัง คำสั่งที่ CI ใช้จริงคือ `pip install -r requirements.txt pytest`
(ไม่ใช่ `requirements-dev.txt`) ซึ่ง **จะพังทันที** เพราะ `requirements.txt` ของ 02 ไม่มี `pytest-asyncio`/
`fakeredis` (แยกไว้ใน `requirements-dev.txt` ตามที่ตั้งใจแยก prod/dev deps) — ต้องแจ้งเฟิส/ทีมกลางถ้าจะเพิ่ม
02 เข้า matrix ว่าให้ใช้ `pip install -r requirements.txt -r requirements-dev.txt` แทน ไม่งั้น CI จะ fail
ทันทีที่เพิ่มเข้าไปทั้งที่โค้ดไม่มีปัญหาอะไร (เขียนเป็นข้อเสนอไว้ใน `handoff/ci.md` แล้วด้วย)

---

## ย้ายจาก main ไปทำงานต่อบน branch `feat/api-backend`

หลัง push งาน 02 เข้า `main` ครั้งแรก (commit `[02] API backend: auth, courses, plans, chat SSE, import,
feedback + tests`) ทีมให้ย้ายมาทำงาน 02 ต่อบน branch **`feat/api-backend`** แทน (branch นี้มีอยู่แล้วบน
origin แต่ตามหลัง `main` ไม่มี commit ของตัวเอง) — sync เข้าด้วยกันด้วย `git checkout -B feat/api-backend
origin/feat/api-backend` แล้ว `git merge --ff-only origin/main` (fast-forward สำเร็จ ไม่มี conflict
เพราะ `feat/api-backend` ไม่เคยมี commit ของตัวเองมาก่อน)

**งาน 02 ทุกอย่างต่อจากนี้ push ไปที่ `origin feat/api-backend` ไม่ใช่ `main`** (`main` คงไว้ตามเดิม ไม่แตะ
ต่อ — commit `[02] API backend: ...` ยังอยู่บน `main` เหมือนเดิมทุกประการ) อัปเดต
`02_api_backend_prompts.md` ส่วน "เตรียมก่อนเริ่ม"/"หลังจบ" ให้ตรงกับ workflow ใหม่นี้แล้ว (checkout/pull/
push ที่ `feat/api-backend`, ห้าม rebase branch ที่ push ไปแล้ว ใช้ `merge` แทนถ้าต้องการของจาก `main`)
