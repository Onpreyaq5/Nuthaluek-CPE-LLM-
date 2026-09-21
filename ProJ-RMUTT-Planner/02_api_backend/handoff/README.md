# handoff/ — ข้อเสนอไฟล์นอกโมดูล + เอกสารส่งมอบ

โฟลเดอร์นี้รวมทุกอย่างที่ `02_api_backend` เตรียมไว้ให้ **เฟิส** (ผู้ดูแลไฟล์ส่วนกลาง/`09_main_app`
ตาม `CONTRIBUTING.md` ของทีม) นำไปพิจารณา — ทีม `02` แก้ไฟล์เหล่านี้เองไม่ได้ตามกติกาโปรเจกต์
(แก้ได้เฉพาะใน `02_api_backend/` เท่านั้น)

## ไฟล์ที่เป็นความรับผิดชอบของเฟิสเท่านั้น (02 ห้ามแก้)

ตาม `CONTRIBUTING.md` หัวข้อ 2 และ 6 — ไฟล์/โฟลเดอร์เหล่านี้ที่ root ของ `ProJ-RMUTT-Planner/`:

- `docker-compose.yml`
- `Makefile`
- `.env.example` (ตัวที่ root ของ repo — คนละไฟล์กับ `02_api_backend/.env.example` ที่ 02 ดูแลเอง)
- `infra/`
- `09_main_app/`
- `.github/workflows/ci.yml`

เมื่อ 02 ต้องการเปลี่ยนแปลงสิ่งใดในไฟล์เหล่านี้ (เช่น เพิ่ม service ใน compose, เพิ่ม job ใน CI)
จะเขียนเป็น**ข้อเสนอ**ไว้ในโฟลเดอร์นี้แทนการแก้ไฟล์จริง — เฟิสเป็นผู้ตัดสินใจว่าจะรับข้อเสนอไปใช้หรือไม่

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | สำหรับ | เนื้อหา |
|---|---|---|
| [`compose.md`](./compose.md) | เฟิส | ข้อเสนอ service `api_backend` ใน `docker-compose.yml` |
| [`ci.md`](./ci.md) | เฟิส | ข้อเสนอ job `api-backend` แยกใน `.github/workflows/ci.yml` (**ไม่ใช่เพิ่มเข้า matrix `python-tests` เดิม** — ดูเหตุผลในไฟล์) |
| [`api-spec.md`](./api-spec.md) | 01, 03-08 | สรุป endpoint ทั้งหมดจาก OpenAPI จริง |
| [`openapi.json`](./openapi.json) | 01, 03-08 | export เต็มจาก `app.openapi()` — import เข้า Postman/Swagger ได้ตรง |
| [`HANDOFF.md`](./HANDOFF.md) | ทุกคน | สถานะแต่ละ endpoint, adapter ไหนยังเป็น mock, known issues, วิธีเดโม |

## หมายเหตุสำหรับเฟิส

- `02_api_backend` ทำงานได้ครบทุก endpoint แล้ว (18 ตัว, D1–D7 ตาม `PLAN.md` เสร็จหมด) โดย **default
  ใช้ mock adapter ทุกโมดูล (03-08)** — ไม่ต้องมีโมดูลอื่นพร้อมก่อนก็รันและเทสต์ `02_api_backend` เองได้ทันที
- ถ้าจะลอง `ADAPTER_05=inprocess` ดูของจริง (05 เริ่มมีโค้ดจริงแล้ว) อ่าน known issue #2 ใน `HANDOFF.md`
  ก่อน — field mapping ระหว่าง 02 กับ 05 ยังไม่เคยยืนยันกันตรงๆ
- `docker compose config` (ที่ CI เช็คอยู่แล้ว) จะยังไม่รู้จัก service `api_backend` จนกว่าจะรับข้อเสนอใน
  `compose.md` เข้าไป — ตอนนี้ยังทดสอบ `02_api_backend` แบบ standalone ผ่าน `scripts/test.sh` /
  `scripts/smoke.sh` ของตัวเองแทน
