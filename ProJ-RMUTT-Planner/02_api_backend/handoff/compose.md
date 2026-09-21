# ข้อเสนอ: env ของ `api_backend` ใน `docker-compose.yml` (root)

โมดูล `02_api_backend` แก้ไฟล์ได้เฉพาะในโฟลเดอร์ตัวเอง (CLAUDE.md ข้อ 12) จึงแก้ `docker-compose.yml`
และ `.env.example` ที่ root เองไม่ได้ — เอกสารนี้เป็น **ข้อเสนอ** ให้ทีมที่ดูแลไฟล์ส่วนกลางนำไปปรับ

## 1. env ที่ service `api_backend` ต้องการเพิ่ม

`02_api_backend/.env.example` มีค่า default ที่ปลอดภัยสำหรับเดโมอยู่แล้วทุกตัว (แอปรันได้แม้ compose
ยังไม่ส่ง env พวกนี้มา) แต่ถ้าจะรันแบบ multi-service จริงตาม PLAN.md ควรเพิ่มใน `docker-compose.yml`:

```yaml
services:
  api_backend:
    environment:
      DATABASE_URL: postgresql+psycopg://rmutt:change_me_please@postgres:5432/rmutt
      REDIS_URL: redis://redis:6379/0
      ADAPTER_04: mock   # เปลี่ยนเป็น http เมื่อ 04 พร้อมรันเป็น service แยก
      ADAPTER_05: mock
      ADAPTER_06: mock
      ADAPTER_07: mock
      ADAPTER_08: mock
      DEMO_USERNAME: admin
      DEMO_PASSWORD: admin1234
      DEMO_STUDENT_ID: "6500000000"
      JWT_SECRET: ${JWT_SECRET}       # ต้องเป็น secret จริงถ้าไม่ใช่ dev
      JWT_EXPIRE_MINUTES: "480"
      SEED_DEMO: "true"               # true เฉพาะ dev/demo เท่านั้น
      ROUTER_URL: http://ai_router:8100   # ดูข้อ 2.1 — อาจต้องเปลี่ยนตามที่ทีมตัดสิน
      CORS_ORIGINS: http://localhost:3000 # ดูข้อ 2.2 — อาจต้องเปลี่ยนตามที่ทีมตัดสิน
```

## 2. จุดขัดกันที่ต้องให้ทีมตัดสิน (02 ไม่ตัดสินเอง)

### 2.1 URL ของโมดูล 03 (AI Router)
- `02_api_backend/PLAN.md` หัวข้อ 3.2 ใช้ `ROUTER_URL=http://router:8001`
- `docker-compose.yml` (root) ตั้งชื่อ service เป็น `ai_router` และรันที่พอร์ต `8100`

**คำถาม**: ให้ `02` ตั้ง `ROUTER_URL=http://ai_router:8100` ให้ตรงกับ compose ที่มีอยู่ หรือจะเปลี่ยนชื่อ/
พอร์ตของ service ใน compose ให้ตรง PLAN.md แทน — เลือกทางใดทางหนึ่งแล้วอัปเดตอีกฝั่งให้ตรงกัน

### 2.2 CORS_ORIGINS / พอร์ตของหน้าเว็บ
- `PLAN.md` หัวข้อ 5 ตั้ง `CORS_ORIGINS=http://localhost:5173` (ค่า default ของ Vite)
- `docker-compose.yml` (root) รัน service `web_app` ที่พอร์ต `3000`

**คำถาม**: ให้ `02` ตั้ง `CORS_ORIGINS=http://localhost:3000` แทน หรือ `01` จะเปลี่ยนมารันที่ 5173

## 3. `ADAPTER_04`/`ADAPTER_05=inprocess` ใน Docker ต้องเปลี่ยน build context

`02_api_backend/Dockerfile` ตอนนี้ตั้ง build context เป็นโฟลเดอร์ `02_api_backend/` เอง (`COPY src/` เท่านั้น)
ทำให้ inprocess loader (อ่านโค้ดของโมดูล 04/05 จากโฟลเดอร์ข้างๆ ผ่าน env `MODULES_ROOT`) หาไฟล์ไม่เจอใน
container เพราะโฟลเดอร์โมดูลอื่นไม่ถูก COPY เข้ามาด้วย

ถ้าทีมต้องการใช้ `ADAPTER_04`/`ADAPTER_05=inprocess` ใน Docker จริง ต้อง:

1. เปลี่ยน build context ของ service `api_backend` เป็น root ของ monorepo แทน `02_api_backend/`:
   ```yaml
   services:
     api_backend:
       build:
         context: .
         dockerfile: 02_api_backend/Dockerfile
   ```
2. แก้ `02_api_backend/Dockerfile` ให้ `COPY` โฟลเดอร์โมดูลที่ต้องการเข้ามาด้วย (เช่น
   `COPY 04_course_data/ ./04_course_data/`, `COPY 05_data_integration/ ./05_data_integration/`)
3. ตั้ง `MODULES_ROOT=/app` ใน container ให้ชี้ไปที่ path ที่ copy โมดูลเหล่านั้นไว้

**ผลกระทบ**: build context ใหญ่ขึ้น (build ช้าลง), โค้ดของ 04/05 กลายเป็นส่วนหนึ่งของ image ของ 02 ไปด้วย
และ 02_api_backend/Dockerfile จะไม่ใช่ไฟล์ที่ "แก้ในโมดูลตัวเองแล้วจบ" อีกต่อไป (ต้องรู้จักโฟลเดอร์อื่น)

ถ้าไม่ต้องการผลกระทบนี้ แนะนำให้ใช้ `ADAPTER_04`/`ADAPTER_05=http` แทน (รันเป็น service แยกใน compose
เหมือน 03) — เป็นทางเลือกที่ตรงไปตรงมากว่าและไม่ต้องแก้ build context
