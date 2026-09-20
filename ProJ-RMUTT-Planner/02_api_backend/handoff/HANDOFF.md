# HANDOFF — 02_api_backend

สถานะล่าสุดหลัง Prompt 1-11 (D1-D7 ตาม PLAN.md ครบ) — เอกสารนี้สำหรับทีมที่จะรับงานต่อ (01, 03-08,
หรือคนตรวจ PR) อ่านคู่กับ [`README.md`](../README.md), [`PROGRESS.md`](../PROGRESS.md) (ละเอียดกว่านี้
รายวัน/รายบั๊ก) และ [`api-spec.md`](./api-spec.md)

## สถานะแต่ละ endpoint

ทุก endpoint ทั้ง 18 ตัว **implement จริงครบแล้ว ไม่มีตัวไหนคืน 501** (ยืนยันด้วย grep โค้ดจริงและ
OpenAPI schema) ทดสอบผ่าน `pytest` กับ Postgres จริง + `fakeredis` ครบทุกตัว มี ownership check
(FORBIDDEN_403 เมื่อไม่ใช่เจ้าของ) ครบทุก resource ที่ผูกกับ student_id

| Endpoint | สถานะ | ทดสอบกับของจริงหรือยัง |
|---|---|---|
| `/auth/login` `/auth/me` `/auth/logout` | ✅ พร้อมใช้ | ✅ Postgres จริง + curl จริง |
| `/courses`, `/courses/{code}/sections` | ✅ พร้อมใช้ | ⚠️ ผ่านแค่ mock adapter 04 (ดูหัวข้อ adapter) |
| `/plans/validate`, `/plans` (CRUD) | ✅ พร้อมใช้ | ⚠️ ผ่านแค่ mock adapter 04/06 |
| `/plans/auto`, `/plans/{id}/explain` | ✅ พร้อมใช้ | ⚠️ ผ่านแค่ mock adapter 06/07 |
| `/chat`, `/chat/sessions`, `/chat/sessions/{id}/messages` | ✅ พร้อมใช้ | ⚠️ ผ่านแค่ mock adapter 03 — **ไม่เคยเห็น response จริงจาก 03 เลย** (ดู known issues) |
| `/students/me/profile`, `/transcript` | ✅ พร้อมใช้ | ⚠️ ผ่านแค่ mock adapter 05 (05 ยังไม่มีฟังก์ชันนี้ใน inprocess mode) |
| `/import` | ✅ พร้อมใช้ | ✅⚠️ ต่อ 05 จริงสำเร็จผ่าน inprocess (`ADAPTER_05=inprocess`) แต่ field mapping ยังไม่ยืนยันความหมายกับทีม 05 (ดู known issue #2) — production ยังใช้ `mock` เป็นค่าเริ่มต้น |
| `/feedback` | ✅ พร้อมใช้ | ⚠️ ส่งเข้า `log_queue` (async batch) ยังไม่เคยยืนยันรูปแบบ event กับ 08 จริง |
| `/health`, `/ready`, `/metrics` | ✅ พร้อมใช้ | ✅ ยืนยันจริงผ่าน Docker container ที่ build จาก Dockerfile จริง |

## Adapter ไหนยังเป็น mock

**ยังใช้ `mock` เป็นค่าเริ่มต้นทุกโมดูล (03-08)** ในการทดสอบ/deploy ปกติ แต่ **05 เริ่มมีโค้ดจริงแล้ว**
(อัปเดตหลังย้ายเข้า repo ทีม — ตอนพัฒนาบนเครื่องแยกยังไม่มี):
- **05**: `05_data_integration/src/graduate_check.py` (parser หน้า "ตรวจสอบจบ") และ `degree_plan.py`
  (`build_plan_input`) **มีโค้ดจริงแล้ว** และ `src/adapters/inprocess/student_data.py` ของ 02 ต่อกับของจริง
  นี้ผ่านทาง `ADAPTER_05=inprocess` ได้แล้ว — ยืนยันด้วย `test_inprocess_student_data_parses_real_fixture`
  ที่ใช้ fixture จริงของ 05 (`05_data_integration/tests/fixtures/graduate_check_sample.html`) **ผ่านจริง**
  (นี่คือการ integration กับของจริงครั้งแรกของโปรเจกต์นี้) แต่ **field mapping ยังเป็นการตีความของ 02 เอง
  ไม่เคยคุยกับทีม 05 ตรงๆ** — ดู known issue #2 ที่อัปเดตแล้ว ค่าเริ่มต้าน `ADAPTER_05` ยังคง `mock` ไว้ก่อน
  จนกว่าจะยืนยัน mapping กับทีม 05
- **04**: ทีมเจ้าของมีโค้ดบางส่วนแล้วเช่นกัน (`04_course_data_services/src/adapters/oreg_rmutt.py` ที่
  `05/degree_plan.py` อ้างถึง) แต่ `src/adapters/inprocess/course_catalog.py` ของ 02 ยังไม่ได้ต่อจริง
  (ทุกเมธอดยัง raise `NotImplementedError` อยู่) — ยังไม่ได้ตรวจว่า contract ตรงกันหรือไม่
- 06, 07, 08: ยังไม่มีสัญญา endpoint จริง (URL/response shape เป็น PLACEHOLDER ทั้งหมดใน `.env.example`)
  `ADAPTER_06=mock`, `ADAPTER_07=mock`, `ADAPTER_08=mock`
- 03 (chat router): ใช้ `http` เสมอตาม CLAUDE.md (ไม่มีโหมด mock ให้เลือกใน production path) แต่ยังไม่มี
  router จริงให้ต่อ — `ROUTER_URL` เป็น placeholder, ทุกการทดสอบ `/chat` ทำผ่าน dependency override เป็น
  mock router ในเทสต์เท่านั้น ไม่เคยยิง HTTP จริงไปหา 03 สักครั้ง

**สรุป:** 05 คือโมดูลแรกที่ต่อ integration จริงสำเร็จ (แม้ยังใช้ `mock` เป็นค่าเริ่มต้นเพราะ field mapping
ยังไม่ยืนยัน) โมดูลอื่น (03, 04 เต็มรูปแบบ, 06, 07, 08) ยังไม่เคยพิสูจน์ integration กับของจริงเลย

## Known issues / สิ่งที่ต้องยืนยันกับทีมก่อนใช้งานจริง

1. **Contract ของ 04-08 ทั้งหมดเป็นการเดา** — path (`PATH_*` ใน `src/adapters/http/*.py`), field ของ
   request/response, error shape เมื่อพัง ไม่มีสัญญาจริงจากทีมเจ้าของโมดูลไหนเลยตอนที่ทำ (ไม่มีไฟล์
   `03_process.txt` ของ 06/07/08 หรือ README ของ 04/05 ให้ยึดในสภาพแวดล้อมนี้)
2. **`StudentContext`/`StudentData.get_transcript()`** (`src/adapters/interfaces.py`) มี field ที่ 02
   กำหนดเอง (`program_name`, `gpax`, `credits_remaining`) — 05 ต้องคืนค่าตามนี้เป๊ะๆ ยังไม่เคยยืนยัน
   (ทั้งสองเมธอดนี้ยัง `NotImplementedError` ใน inprocess mode — 05 ยังไม่มีฟังก์ชันสำหรับสองอันนี้)

   **อัปเดต (หลังพบว่า 05 มีโค้ดจริงแล้ว)**: `import_graduate_check()` ต่อกับของจริงสำเร็จแล้ว
   (`InprocessStudentData.import_graduate_check`) แต่ field ของ `ImportResult` ที่ map มาจาก
   `DegreeAudit`/`DegreePlanInput` จริงของ 05 (`imported_courses = len(audit.all_courses())`,
   `retake_required` = รหัสวิชาจาก `audit.failed_courses()`, `credits_remaining = plan_input.remaining_total`,
   `warnings = []` เพราะ 05 ไม่มีแนวคิด "warning" ตรงๆ) **เป็นการตีความของ 02 เอง ยังไม่เคยคุยกับทีม 05**
   ว่าความหมายที่ต้องการตรงกับนี้ไหม — ก่อนตั้ง `ADAPTER_05=inprocess` ใช้งานจริง ต้องยืนยันจุดนี้ก่อน
   (โค้ดจริง: `05_data_integration/src/graduate_check.py` มี `parse_graduate_check()`,
   `05_data_integration/src/degree_plan.py` มี `build_plan_input()` — อ่านได้เพื่อดู field ทั้งหมด)
   ทดสอบ: `tests/unit/test_inprocess_student_data_integration.py::test_inprocess_student_data_parses_real_fixture`
   ผ่านจริงด้วย fixture จริงของ 05 ส่วน `test_inprocess_import_matches_expected_json` ถูก skip ไว้ตั้งแต่
   ตอนนี้เพราะ fixture สังเคราะห์ของ 02 เอง (`fixtures/import/sample_sanitized.html`) เป็นรูปแบบ "รายงาน
   ผลการศึกษา" ทั่วไป ไม่ตรงกับหน้า "ตรวจสอบจบ" จริงที่ parser ของ 05 ต้องการ (ต้องขอตัวอย่างหน้าจริงที่ลบ
   ข้อมูลระบุตัวตนแล้วจากทีม 05 มาแทนไฟล์นี้ถึงจะทดสอบ end-to-end กับข้อมูลของเราเองได้)
3. **`src/models/student.py`** (ตาราง `students`, `student_preferences`) field เดาเองทั้งหมด เพราะไม่มี
   `00_docs/05_data_model.md` ให้ยึด — ถ้าโครงจริงต่างจากนี้ ต้องแก้ migration (มี 0001-0004 ต่อกันแล้ว
   แก้ 0001 ตรงๆ ได้เพราะยังไม่มีใครใช้ข้อมูลจริง)
4. **`TOOL_ALLOWLIST`** (`search_knowledge,search_courses,check_schedule_conflict,generate_plan`) เดาเอง
   เพราะไม่มีไฟล์ INTENT→TOOL MAP ของ 03 — ต้องยืนยันชื่อ tool จริงกับทีม 03
5. **`CURRENT_TERM`** เป็นค่าคงที่ตัวเดียวที่ส่งให้ 03 ทุก session (ไม่มี field term จาก 01 ในคำขอแชต) —
   ต้องตัดสินว่าควรมาจากเทอมปัจจุบันของระบบ/เทอมของแผนล่าสุด/ให้ 01 ส่งมาเพิ่ม
6. **`plan.last_validation` เป็น null เสมอ** — ตัดสินใจว่า `POST /plans` (save) ไม่เรียก 05/06 ซ้ำ
   ตาม PLAN.md 4.3 ที่เขียนว่า POST/GET /plans เรียกแค่ DB (ต่างจาก `/plans/validate` ที่ระบุ 05→06
   ชัดเจน) — ถ้าต้องการให้ save พร้อมผลตรวจล่าสุดด้วย ต้องยืนยันก่อนเพราะขัดกับตารางที่เขียนไว้
7. **`intent` column ใน `chat_messages`** ไม่เคย populate เลย เพราะ event ตาราง 6.2 ไม่มี field นี้จาก 03
8. **`LogSink.send_feedback()`** (มีมาตั้งแต่ Prompt 3) ไม่เคยถูกเรียกใช้จริงเลย — feedback ทั้งหมดไปทาง
   `log_queue.enqueue()` (เหมือน validate/auto/chat) แทนตามที่ Prompt 9 สั่ง เมธอดนี้เป็น dead code
   ในทางปฏิบัติ ควรตัดสินใจว่าจะลบทิ้งหรือใช้งานจริงในอนาคต
9. **`POST /students/me/import`** ตรวจเนื้อหาไฟล์ไม่เชื่อ content-type/นามสกุลจริง แต่ "ตรวจระหว่างอ่าน
   ไม่อ่านทั้งไฟล์ก่อน" ทำได้ไม่เต็มร้อยตามตัวอักษร เพราะ FastAPI/Starlette parse multipart ทั้งก้อนไว้
   ก่อนโค้ดเราควบคุมอะไรได้ (ต้องเขียน ASGI multipart parser เองถึงจะทำได้เต็มรูปแบบ — เกินขอบเขตที่ทำไป)
10. **คุกกี้ `Secure` flag** อ่านจาก `settings.CORS_ORIGINS.startswith("https://")` (`src/api/v1/auth.py`)
    — ถ้าตั้ง `CORS_ORIGINS` เป็นหลาย origin คั่นด้วย comma และตัวแรกไม่ใช่ https (แต่ตัวหลังเป็น) จะได้
    `Secure=False` ทั้งที่ origin จริงที่ใช้อาจเป็น https ก็ได้ — ในทางปฏิบัติยังไม่เป็นปัญหาเพราะ dev ใช้
    origin เดียว แต่ถ้า production มีหลาย origin ควรพิจารณาแก้ไข
11. **ไม่มี `docker-compose.yml` ที่ root ของ repo** ในสภาพแวดล้อมนี้ (ข้อเสนออยู่ที่ `handoff/compose.md`
    ให้ทีมนำไปรวมเอง) — `scripts/test.sh`/`scripts/smoke.sh` ใช้ `docker run` + `docker network` แทน
12. **ไม่มี git repository ในสภาพแวดล้อมนี้เลย** (`git status` → "not a git repository") — โค้ดทั้งหมด
    เป็นไฟล์ในโฟลเดอร์ `02_api_backend/` เท่านั้น ยังไม่เคย commit/push จริง ทีมที่รับงานต่อต้อง `git init`
    (หรือ copy เข้า repo จริงของทีม) เองก่อน — เพิ่ม `.gitignore` ไว้ให้แล้ว (`.venv/`, `__pycache__/`,
    `.env`, cache ต่างๆ) เพื่อกันปัญหาตอน commit ครั้งแรก ไม่มีไฟล์ใดถูกสร้าง/แก้นอก `02_api_backend/`
    เลยตลอดทั้งโปรเจกต์ (ยืนยันด้วยการตรวจโฟลเดอร์ `E:\ML` ว่ามีแค่ `02_api_backend/` อยู่ข้างในเท่านั้น)

## ตรวจความปลอดภัยรอบสุดท้าย (Prompt 11)

- ✅ ไม่มี log ใดที่มีชื่อ/รหัสนักศึกษาจริงหรือเนื้อข้อความแชต — grep `logger.*(info|warning|error)` ทุกจุด
  แล้ว มีแต่ `count`, `scope`, `key` (cache key จาก course params ไม่ใช่ PII), `error_type` เท่านั้น
- ✅ `id_hash` (ไม่ใช่ `student_id` ดิบ) เท่านั้นที่ส่งออกนอก 02 ไปยัง 03 · ข้อความแชตผ่าน `scrub_text()`
  ก่อนส่งทุกครั้ง (ทั้งข้อความใหม่และ history) · `log_queue` ผ่าน `mask_payload()` ก่อนเข้าคิวเสมอ
- ✅ cookie `session`: `HttpOnly=True`, `SameSite=Lax`, `Path=/` ครบ (ดูข้อ known issue #10 เรื่อง `Secure`)
- ✅ `CORS_ORIGINS` มี validator บังคับห้ามเป็น `"*"` เมื่อ `allow_credentials=True` (`src/core/config.py`)
- ✅ ไม่มีไฟล์ `.env` จริงถูกสร้าง/commit ในโปรเจกต์ (มีแค่ `.env.example`) ไม่พบ secret/API key ที่ hardcode
- ✅ ไม่พบรหัสนักศึกษารูปแบบจริง (`1xxxxxxxxxxx-x`) อยู่นอก `tests/`/`fixtures/` เลย
- ✅ เพิ่ม `.gitignore` กัน `.venv/`, `__pycache__/`, `.env`, cache ไม่ให้หลุดเข้า commit แรกในอนาคต

## วิธีเดโมทีละขั้นด้วยบัญชี admin

```bash
# 1) เตรียม Postgres + Redis (ตัวอย่างด้วย docker run ตรง ๆ เพราะไม่มี compose.yml ที่ root)
docker run -d --name demo-pg -e POSTGRES_USER=rmutt -e POSTGRES_PASSWORD=change_me_please \
  -e POSTGRES_DB=rmutt -p 5432:5432 postgres:16-alpine
docker run -d --name demo-redis -p 6379:6379 redis:7-alpine

# 2) ตั้งค่าและ migrate + seed บัญชีเดโม
cp .env.example .env    # ค่าเริ่มต้นพอสำหรับเดโม ไม่ต้องแก้อะไร
alembic upgrade head
python -m scripts.seed_demo     # สร้าง admin/admin1234 (student_id เดโม 6500000000)

# 3) รันเซิร์ฟเวอร์
python -m uvicorn src.main:app --reload      # Linux/Mac
python scripts/run_dev.py                    # Windows

# 4) เดโม flow เต็ม (เปิด http://localhost:8000/docs เพื่อเดโมผ่าน Swagger UI ก็ได้)
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" -d '{"username":"admin","password":"admin1234"}'
curl -b cookies.txt http://localhost:8000/api/v1/courses
curl -b cookies.txt -X POST http://localhost:8000/api/v1/plans/validate \
  -H "Content-Type: application/json" -d '{"term":"1/2569","section_ids":["CPE201-01"]}'
curl -b cookies.txt -X POST http://localhost:8000/api/v1/plans \
  -H "Content-Type: application/json" -d '{"term":"1/2569","name":"แผนหลัก","section_ids":["CPE201-01"]}'
curl -b cookies.txt http://localhost:8000/api/v1/plans
curl -b cookies.txt -X POST http://localhost:8000/api/v1/plans/auto \
  -H "Content-Type: application/json" -d '{"term":"1/2569"}'
curl -b cookies.txt -N -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" -d '{"session_id":null,"message":"ลงทะเบียนตอนไหน"}'
  # ได้ UPSTREAM_502 เพราะยังไม่มี router 03 จริงให้ต่อ — เป็นพฤติกรรมที่ถูกต้องในสภาพแวดล้อมนี้
curl -b cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

หรือรัน `sh scripts/smoke.sh` เพื่อดู flow เดียวกันนี้แบบอัตโนมัติทั้งหมด (build image, ตั้ง
Postgres/Redis ชั่วคราวเอง, รันครบ, cleanup ให้เองหลังจบ)

## เอกสารอื่นที่เกี่ยวข้อง

- [`api-spec.md`](./api-spec.md) + [`openapi.json`](./openapi.json) — รายละเอียด endpoint ทุกตัว
- [`compose.md`](./compose.md), [`ci.md`](./ci.md) — ข้อเสนอไฟล์นอกโมดูล (compose.yml, CI) ให้ทีมกลาง
  เอาไปรวมเอง (02 ไม่แก้ไฟล์เหล่านี้เอง)
- [`../PROGRESS.md`](../PROGRESS.md) — บันทึกละเอียดรายวันของทุก prompt (บั๊กที่เจอ/แก้ยังไง, สมมติฐาน
  ทั้งหมด, คำสั่งทดสอบซ้ำ)
- [`../PLAN.md`](../PLAN.md) หัวข้อ 8 — checklist D1-D7 (ครบทุกข้อยกเว้น "เปลี่ยน adapter เป็นของจริง"
  ใน D5 ซึ่งรอ 04-08 มีโค้ดจริงก่อน) และหัวข้อ 12 — คำถามที่ยังไม่มีคำตอบจากทีม
