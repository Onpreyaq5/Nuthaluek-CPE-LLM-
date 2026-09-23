# หน้าเว็บ 01 ตัวเต็ม — Docker project แยก (`rmutt-webapp`)

ยกหน้าเว็บ CampusMate (โมดูล 01) พร้อมบริการทุกตัวที่มันเรียก ต่อข้อมูลจริงครบทุกหน้า
แยกจากชุดหลักที่รากโปรเจกต์ทั้งชื่อ project, network และ volume — รันพร้อมกันได้ไม่ชนกัน

## รัน

```bash
cd ProJ-RMUTT-Planner
cp .env.example .env            # ครั้งแรกเท่านั้น
docker compose -f deploy/webapp/docker-compose.yml --env-file .env up -d --build
```

เปิด http://localhost:4001 แล้ว login `admin` / `admin1234` · Grafana ที่ http://localhost:4002

**ใส่คีย์ Gemini** (ไม่ใส่ก็ใช้ได้ คำถามทั่วไปจะตอบด้วยโมเดลในเครื่อง ส่วนระเบียบจะยกข้อความจากเอกสาร)
ใส่ที่ `GEMINI_API_KEY` ใน `.env` หรือเก็บในไฟล์แยกนอกโปรเจกต์แล้วส่งเพิ่มอีกไฟล์:

```bash
docker compose -f deploy/webapp/docker-compose.yml --env-file .env --env-file ~/secrets/gemini.env up -d
```

**ลิงก์สาธารณะ** (ใช้ได้เฉพาะตอนเครื่องนี้เปิดอยู่ ลิงก์เปลี่ยนทุกครั้งที่สั่งขึ้นใหม่):

```bash
docker compose -f deploy/webapp/docker-compose.yml --env-file .env --profile public up -d tunnel
docker compose -f deploy/webapp/docker-compose.yml logs tunnel | grep trycloudflare
```

## ตรวจว่าใช้งานได้ครบ

```bash
python deploy/webapp/verify.py                  # หรือใส่ลิงก์สาธารณะต่อท้าย
```

ยิงทุกฟีเจอร์ผ่านทางเดียวกับเบราว์เซอร์ 21 ข้อ: login, ค้นรายวิชา/กรองวัน, ตรวจตารางชนด้วยคู่ที่ชนจริง,
จัดตารางอัตโนมัติ, บันทึก/อธิบาย/ลบแผน, feedback, โปรไฟล์, นำเข้าไฟล์ตรวจสอบจบ,
แชต 4 แบบ (ระเบียบ, วิชาบังคับก่อน, ตารางชน, คำถามทั่วไป) และประวัติแชต

## เส้นทางของแต่ละฟีเจอร์

| ฟีเจอร์ในหน้าเว็บ | ไหลผ่าน |
|---|---|
| ค้นรายวิชา / กลุ่มเรียน | 01 → 02 → 04 (ตารางสอนจริงจาก `09_main_app/data/seed`) |
| ตรวจตารางชน | 01 → 02 → 06 → 04 · ผลจาก 05 (วิชาที่ผ่านแล้ว) |
| จัดตารางอัตโนมัติ | 01 → 02 → 06 (CP-SAT) → 04 |
| อธิบายแผน | 01 → 02 → 07 |
| โปรไฟล์ / นำเข้าผลการเรียน | 01 → 02 → 05 |
| แชต | 01 → 02 → 03 เลือก AI → 07 (RAG + Qdrant) / Gemini / Local AI หรือเครื่องมือ 04/06 |
| feedback / log | 01 → 02 → 08 → Prometheus → Grafana |
