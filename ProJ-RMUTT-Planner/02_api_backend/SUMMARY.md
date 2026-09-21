# สรุปงาน — 02_api_backend (RMUTT Study Planner API Gateway)

เอกสารสรุปภาพรวมสำหรับส่งให้เพื่อนในทีม (01, 03-08) อ่านคร่าวๆ ก่อน — รายละเอียดลึกกว่านี้ดูไฟล์ที่ลิงก์ไว้ท้ายเอกสาร

## นี่คืออะไร

`02_api_backend` คือ **API Gateway** ของระบบวางแผนการเรียน RMUTT Study Planner — เป็นทางเข้าเดียวที่
หน้าเว็บ (โมดูล 01) เรียกใช้ ตัวมันเองไม่มีตรรกะคำนวณเอง แค่รวบรวม/ส่งต่อไปยังโมดูลอื่น:
- **03** (AI router) → ตอบแชต
- **04** (course catalog) → ข้อมูลรายวิชา
- **05** (student data) → ข้อมูลนักศึกษา/transcript
- **06** (schedule conflict engine) → ตรวจตารางชน/prerequisite
- **07** (explainer) → อธิบายเหตุผลของแผนเป็นภาษาคน
- **08** (log sink) → เก็บ log/feedback

## สถานะ: ทำเสร็จครบ 11/11 prompt แล้ว (D1–D7 ตาม PLAN.md)

ทุก endpoint ที่ตกลงกันไว้ **implement จริงครบทั้ง 18 endpoint ไม่มีตัวไหนคืน 501 (ยังไม่ทำ) เลย**

| กลุ่ม | Endpoint |
|---|---|
| Auth | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| วิชา | `GET /courses`, `GET /courses/{code}/sections` |
| แผนการเรียน | `POST /plans/validate`, `POST /plans`, `GET /plans`, `GET /plans/{id}`, `DELETE /plans/{id}`, `POST /plans/auto`, `GET /plans/{id}/explain` |
| แชต | `POST /chat` (SSE), `GET /chat/sessions`, `GET /chat/sessions/{id}/messages` |
| นักศึกษา | `GET /students/me/profile`, `GET /students/me/transcript`, `POST /students/me/import` |
| อื่นๆ | `POST /feedback`, `GET /health`, `GET /ready`, `GET /metrics` |

รวมของ "ความเรียบร้อยระบบ" (D6) ด้วย: rate limit (Redis), `/ready`+`/metrics`, ปักเวอร์ชัน dependency
(`requirements.lock`), smoke test อัตโนมัติ (`scripts/smoke.sh`), เอกสารครบ

## ⚠️ สิ่งสำคัญที่สุดที่ต้องรู้: ทุก endpoint ยังทดสอบกับ "ข้อมูลจำลอง" (mock) เท่านั้น

โมดูล **03–08 ยังไม่มีโค้ดจริงให้ต่อสักตัวเดียว** ตอนที่ทำงานนี้ — ทุกการทดสอบผ่าน adapter แบบ `mock`
(ข้อมูลสังเคราะห์ในโค้ด) ทั้งหมด โค้ดฝั่ง 02 ออกแบบให้สลับไปใช้ของจริงได้ทันทีที่แต่ละโมดูลพร้อม (แค่เปลี่ยน
env `ADAPTER_04..08=http` + ใส่ URL จริง) **แต่ยังไม่เคยพิสูจน์ว่าต่อกับของจริงแล้วทำงานถูกต้อง**

field/URL ของแต่ละโมดูลที่ 02 คาดหวังไว้เป็นการ**เดาทั้งหมด** เพราะไม่มีสัญญา (contract) จริงให้ยึดตอนทำ
— รายละเอียดที่ต้องคุยกันก่อนต่อของจริง ดูหัวข้อ "สิ่งที่ต้องคุยกับทีม" ด้านล่าง

## ทดสอบผ่านหมดแล้ว

- `pytest -q` → **190 ผ่าน, 2 skip** (2 ตัวที่ skip รอโมดูล 05 มีโค้ดจริงถึงจะรันได้)
- `ruff check .` → ผ่านหมด (โค้ดสไตล์สะอาด)
- `scripts/smoke.sh` → จำลองรันจริงทั้งระบบ (build Docker image + Postgres + Redis จริง) แล้วยิง
  login → ดูวิชา → ตรวจตารางชน → บันทึกแผน → แชต ผ่านครบทุกขั้นตอน

## วิธีลองรันเอง (แบบเร็ว)

```bash
cd 02_api_backend
cp .env.example .env
docker build -t rmutt-api .
# ต้องมี Postgres + Redis จริงก่อน (ดู README.md สำหรับตัวอย่างเต็ม)
docker run -p 8000:8000 --env-file .env rmutt-api
```
เปิด `http://localhost:8000/docs` ดู API แบบ interactive ได้เลย บัญชีเดโม: `admin` / `admin1234`

หรือรัน `sh scripts/smoke.sh` เพื่อดูทั้งระบบทำงานจริงแบบอัตโนมัติ (ไม่ต้อง setup อะไรเอง)

## สิ่งที่ต้องคุยกับทีมก่อนต่อของจริง

1. **04/05/06/07/08**: URL, path, รูปแบบ request/response ที่ 02 คาดหวังไว้ ต้องเทียบกับของจริงแต่ละทีม
2. **03 (AI router)**: ชื่อ tool ที่อนุญาต (`TOOL_ALLOWLIST`), รูปแบบ event SSE — 02 กำหนดเองไว้คร่าวๆ
3. **05**: field ของ `StudentContext` (`program_name`, `gpax`, `credits_remaining` ฯลฯ) ที่ 02 คาดหวัง
4. โครงสร้างตาราง `students`/`student_preferences` ในฐานข้อมูลของ 02 เป็นการเดาเอง เพราะไม่มีเอกสาร
   data model ให้ยึดตอนทำ

รายละเอียดเต็มของทุกข้อ + known issues อื่นๆ: ดู `handoff/HANDOFF.md`

## เอกสารอื่นที่เกี่ยวข้อง (ในโฟลเดอร์ `02_api_backend/`)

| ไฟล์ | เนื้อหา |
|---|---|
| `README.md` | วิธีรันแบบละเอียด, env vars, curl ตัวอย่างทุก endpoint |
| `handoff/HANDOFF.md` | สถานะแต่ละ endpoint, known issues ทั้งหมด, วิธีเดโมทีละขั้น |
| `handoff/api-spec.md` + `handoff/openapi.json` | รายละเอียด API ทุกตัว (import เข้า Postman ได้) |
| `PLAN.md` | แผนงานเต็ม + checklist ที่ทำไปแล้ว |
| `PROGRESS.md` | บันทึกละเอียดรายวัน (บั๊กที่เจอ, สมมติฐานที่ใช้, การตัดสินใจแต่ละจุด) |
| `handoff/compose.md`, `handoff/ci.md` | ข้อเสนอ docker-compose.yml และ CI ให้ทีมกลางนำไปใช้ |

หมายเหตุ: งานนี้ยังไม่ได้ทำ git commit/push (ยังไม่มี git repo) — ถ้าจะรวมเข้า repo กลาง ต้อง `git init`
หรือ copy โค้ดในโฟลเดอร์ `02_api_backend/` นี้เข้า repo จริงก่อน
