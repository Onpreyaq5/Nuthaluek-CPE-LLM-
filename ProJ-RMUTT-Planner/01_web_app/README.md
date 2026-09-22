# CampusMate — 01 Web App

ต้นแบบเว็บภาษาไทยสำหรับผู้ช่วยข้อมูลมหาวิทยาลัยและวางแผนลงทะเบียน ใช้ React + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui พร้อมมาสคอตและข้อมูลสังเคราะห์

ฉบับนี้ทำตาม `01_web_app_work_plan.md` เพื่อทดลองหน้าตาและ workflow ก่อนเชื่อมระบบคนอื่น **ยังไม่ได้เชื่อม Backend หรือโมเดลจริง** และยังไม่ใช่ระบบลงทะเบียนจริง

## เริ่มใช้งาน

ใช้ Node.js 22 หรือ 24 และ npm จากนั้นเปิด terminal ในโฟลเดอร์นี้:

```sh
npm ci
npm run dev
```

เปิด http://127.0.0.1:5173 แล้วใช้ **admin / admin1234** หรือกด “กรอกให้ฉัน”

ไม่จำเป็นต้องสร้าง `.env` สำหรับทดลอง ค่าเริ่มต้นเปิด mock ไว้ หากต้องการกำหนดเองให้คัดลอก `.env.example` เป็น `.env.local`

## สิ่งที่ทดลองได้

| หน้า | การทำงาน |
|---|---|
| เข้าสู่ระบบ | บัญชีตัวอย่าง, แจ้งรหัสผิด, logout, จำลอง session หมดอายุ |
| แชต | ประวัติ, บทสนทนาใหม่, คำตอบทยอยมาแบบ POST SSE, หยุดตอบ, แหล่งอ้างอิง, คัดลอก, feedback |
| ค้นหารายวิชา | ค้นหา, กรองวันและอาจารย์, แบ่งหน้า, เลือก section, ปิดปุ่ม section ที่นั่งเต็ม |
| จัดตารางเรียน | ตารางจันทร์–เสาร์ 08:00–20:00, ตรวจแผนอัตโนมัติ, แสดงเวลาชน, เปลี่ยน section, บันทึกแผน |
| แผนที่บันทึก | รายการ, รายละเอียด, คำอธิบาย, ใช้เป็นแผนร่าง, ยืนยันก่อนลบ |
| สร้างแผนอัตโนมัติ | กำหนดวันว่าง/หน่วยกิต/คงวิชาที่เลือก, เปรียบเทียบตัวเลือกจากชุดข้อมูลจำลอง |
| ข้อมูลการเรียน | โปรไฟล์, ดาวน์โหลด HTML ตัวอย่าง, นำเข้าไฟล์, ตารางผลการเรียนและวิชาที่ต้องลงใหม่ |

บนมือถือเมนูจะอยู่ในปุ่มด้านซ้ายบน และตารางเรียนเปลี่ยนเป็นรายการรายวัน

## ลำดับทดลองที่แนะนำ

1. เข้าสู่ระบบ → ทดลองอ่านข้อความและเปิดแหล่งอ้างอิงในแชต
2. ค้นหารายวิชา → เลือก **CPE201 section 01** กับ **CPE203 section 01**
3. จัดตารางเรียน → พบเวลาชนและปุ่มบันทึกไม่พร้อมใช้
4. คลิกคาบ CPE203 → เปลี่ยนเป็น **section 02** → ผลตรวจผ่าน → บันทึกชื่อแผน
5. เปิดแผนที่บันทึก แล้วรีเฟรชเพื่อดูว่าข้อมูลยังอยู่
6. จัดตารางเรียน → “ให้ช่วยจัดแผน” → สร้างและเปรียบเทียบตัวเลือก
7. ข้อมูลการเรียน → ดาวน์โหลดไฟล์ตัวอย่าง → นำเข้า HTML → แสดง 5 รายวิชา

ข้อความทดสอบแชต:

- `ทดสอบ stream ขาด` — จบการเชื่อมต่อโดยไม่มี done ต้องขึ้นคำตอบขาดกลางทาง
- `ทดสอบ stream error` — ส่ง error ระหว่างตอบ
- `ทดสอบ 502` — จำลองบริการปลายทางไม่พร้อมใช้
- คำถามทั่วไป — แสดงคำตอบ fixture ตามกลุ่มคำถาม ไม่ได้เรียก LLM

## ข้อมูลจำลองและการเก็บสถานะ

- MSW ดัก request `/api/v1/*` ในเบราว์เซอร์ และตอบตาม contract จำลอง
- ข้อมูลตัวอย่างเก็บใน localStorage ชื่อ `campusmate-demo-v2-data`; สถานะ login จำลองเก็บใน sessionStorage ชื่อ `campusmate-demo-session` ไม่มี JWT/token ใน browser storage
- **mock login ไม่ได้จำลองความปลอดภัยของ HttpOnly cookie** การเชื่อมจริงต้องใช้ cookie จาก Backend และทดสอบ auth/CSRF แยกต่างหาก
- แผนร่างยังไม่บันทึกจะอยู่ในหน่วยความจำ รีเฟรชแล้วหาย; แผนที่กดบันทึกจะอยู่ต่อ
- โปรไฟล์และวิชาเป็นสังเคราะห์ แสดงเพียงภาคเรียน 1/2569
- ตัวนำเข้า mock ยอมรับเฉพาะไฟล์ตัวอย่างที่มี marker `campusmate-demo-transcript` และคืน fixture ไม่ใช่ parser ผลการเรียนจริง ไม่แสดงหรือรัน HTML ที่อัปโหลด
- แผนอัตโนมัติเป็นการกรองชุดตัวเลือกที่เตรียมไว้ ไม่ใช่ solver หลักสูตรจริง
- ใช้แท็บเดียวต่อการทดลองเพื่อหลีกเลี่ยงข้อมูลจำลองจากหลายแท็บเขียนทับกัน

## ส่งต่อให้ Backend

ดู [HANDOFF.md](HANDOFF.md) สำหรับ endpoint, request/response, event ของ SSE และรายการที่ต้องตกลงกับ 02/08

```dotenv
VITE_USE_MOCKS=false
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
```

แก้ `.env.local` แล้ว restart Vite หน้าเว็บเรียก `/api/v1` บน origin เดียวเสมอโดยแนบ cookie ผ่าน `credentials: include` ตัว proxy ใช้เฉพาะตอนพัฒนา ค่า `VITE_*` ห้ามใส่ secret

`contracts/demo-openapi.json` เป็น **ข้อเสนอ contract สำหรับต้นแบบ** ไม่ใช่ OpenAPI ที่ทีม 02 ยืนยันแล้ว เมื่อได้รับไฟล์จริงให้ปรับ request/response และสร้าง type ใหม่:

```sh
npm run gen:api -- http://127.0.0.1:8000/openapi.json -o src/api/schema.d.ts
npm run typecheck
```

อาจต้องแก้ alias ใน `src/api/types.ts` ให้ตรงชื่อ schema ของ Backend ห้ามถือว่าปิด mock แล้วเชื่อมได้ทันทีโดยไม่ตรวจ contract

## Build และตรวจงาน

```sh
npm run typecheck
npm test
npm run build
npm run preview
```

`npm test` ใช้ Node.js test runner และ bundle test ด้วย esbuild แทน Vitest เพื่อให้เรียกตัว bundler โดยตรงได้ในสภาพแวดล้อม Windows ที่จำกัด subprocess มี 11 cases สำหรับ SSE, envelope, multipart และตำแหน่งคาบเรียน

`dist/` คือ static files ที่ส่งให้ 08 หรือให้ FastAPI serve ได้ โดยต้องมี SPA fallback สำหรับเส้นทางหน้าเว็บ และต้องไม่ fallback `/api/*` เป็น HTML

## Docker

```sh
docker build -t campusmate-web-demo .
docker run --rm -p 8080:80 campusmate-web-demo
```

เปิด http://localhost:8080 โดย Service Worker ใช้ได้บน localhost หรือ HTTPS

พัฒนาใน container:

```sh
docker build -f Dockerfile.dev -t campusmate-web-dev .
docker run --rm -p 5173:5173 campusmate-web-dev
```

เมื่อเชื่อมจริง:

```sh
docker build --build-arg VITE_USE_MOCKS=false -t campusmate-web .
docker run --rm --network campusmate -p 8080:80 -e API_UPSTREAM=http://api-backend:8000 campusmate-web
```

network และชื่อ `api-backend` เป็นตัวอย่างที่ 08 ต้องจัดให้ตรง Compose จริง Dockerfile นี้เป็น container ของ **เว็บเท่านั้น** หากทีมกำหนด application container เดียวในตอนท้าย ให้รวม `dist/` เข้า runtime ที่ 02/08 เตรียมไว้ ไม่ใช่นำ Docker images มารวมกันโดยตรง

## โครงสร้างที่แก้ต่อ

```text
src/App.tsx                routes, login, sidebar, auth guard
src/features/              หน้าจอหลักทั้งหมด
src/components/            มาสคอต, แหล่งอ้างอิง, ตารางเรียน, UI
src/api/client.ts          API envelope + cookie + error + timeout
src/api/chat-stream.ts     POST SSE + UTF-8 buffering + cancellation
src/api/schema.d.ts        generated types
src/mocks/                 MSW + ข้อมูลสังเคราะห์
src/i18n/th.ts             ข้อความภาษาไทยของหน้าเว็บ
src/index.css              โทนสีและ responsive layout
public/mascot.png          มาสคอต
contracts/                 OpenAPI จำลองที่ใช้คุยกับทีม
```

## พรีวิวสำรองสำหรับเครื่องนี้

ระหว่างพัฒนาบนเครื่องนี้ Vite เปิด child process ของ esbuild ไม่ได้ (`spawn EPERM`) จึงตรวจเว็บผ่าน `preview-dist/` ที่สร้างจาก source ชุดเดียวกันด้วย esbuild executable และ Tailwind compiler โดยตรง พร้อม static server ใน `scripts/serve-preview.mjs`

ไฟล์พรีวิวสำเร็จรูปแจกแยกเป็น ZIP; แตก ZIP แล้วรัน `node serve-preview.mjs` โดยไม่ต้อง npm install ส่วนโค้ดหลักยังเป็น Vite ตาม stack ที่ตกลง วิธีนี้ไม่ได้ยืนยันว่า Vite build และ Docker ผ่านแล้ว ดูผลตรวจใน [VERIFICATION.md](VERIFICATION.md)

โค้ดนี้ไม่มีการเพิ่มเครดิตผู้สร้างจากเครื่องมือช่วยเขียนงาน; ใบอนุญาตของ dependency เก็บไว้ตามเดิมใน `THIRD_PARTY_NOTICES.md`
