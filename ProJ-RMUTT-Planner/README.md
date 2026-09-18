# RMUTT Study Planner 🎓

ระบบ **วางแผนการเรียนและจัดตารางเรียนอัตโนมัติ** สำหรับนักศึกษามหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี
จุดขายหลัก: **ตรวจ "ตารางชน" ได้แม่นยำ 100%** + AI ช่วยจัดแผนการเรียนและตอบคำถามระเบียบโดยอ้างอิงเอกสารจริง

> โปรเจกต์กลุ่มรายวิชา LLM — ทุก service รันบน Docker, แบ่งโฟลเดอร์ตามหน้าที่ 1 โฟลเดอร์ = 1 เจ้าของ

---

## ทำอะไรได้บ้าง

| ฟีเจอร์ | อธิบาย |
|---|---|
| ✅ เช็คตารางชนแบบทันที | ลากวิชาลงตาราง เห็นเลยว่าชนกับตัวไหน ช่วงเวลาไหน |
| ✅ ตรวจสอบครบทุกเงื่อนไข | เวลาเรียนชน / เวลาสอบชน / วิชาบังคับก่อน / หน่วยกิตเกิน / ที่นั่งเต็ม / ลงซ้ำ |
| 🤖 จัดตารางให้อัตโนมัติ | บอกความชอบ (ไม่เรียนเช้า, อยากว่างศุกร์) → ระบบเสนอ 3-5 แผน |
| 🤖 อธิบายเป็นภาษาคน | "วิชา A ชนกับ B ตอนจันทร์ 9 โมง ลองเปลี่ยนเป็นหมู่ 05 ดูไหม" |
| 📚 ถาม-ตอบระเบียบ (RAG) | "ถอนวิชาได้ถึงเมื่อไหร่" → ตอบพร้อมอ้างอิงข้อบังคับ หน้าไหน ข้อไหน |
| 📅 แจ้งเตือน | ใกล้วันลงทะเบียน, ที่นั่งใกล้เต็ม, วิชาที่วางแผนไว้เปลี่ยนเวลา |
| 📊 Dashboard | วิชาที่ชนบ่อย, คำถามยอดฮิต, คำถามที่ระบบตอบไม่ได้ |

---

## โครงสร้างโปรเจกต์

```
ProJ-RMUTT-Planner/
│
├── 00_docs/                          # 📖 เอกสารกลาง — อ่านก่อนเริ่มเขียนโค้ด
│   ├── 01_architecture.md            #   สถาปัตยกรรมทั้งระบบ + แผนผัง
│   ├── 02_mindmap.md                 #   มายด์แมปข้อมูล (ข้อมูลอะไรบ้าง ไหลไปไหน)
│   ├── 03_flow.md                    #   Flow การทำงาน 5 เส้นทาง + Sprint Plan
│   ├── 04_team_roles.md              #   แบ่งงาน + กติกา Git + Definition of Done
│   └── 05_data_model.md              #   Schema ฐานข้อมูล (SQL)
│
├── 01_web_app/                       # หน้าเว็บนักศึกษา (Next.js)          :3000
├── 02_api_backend/                   # API / Auth / Gateway (FastAPI)      :8000
├── 03_ai_router_agent/               # จับ intent + เลือก tool + คุม context :8100
├── 04_course_data_services/          # ดึงข้อมูลรายวิชา/ตารางสอน/ปฏิทิน      :8400
├── 05_data_integration/              # normalize เวลา + prereq graph + context :8500
├── 06_schedule_conflict_engine/      # ★ ตรวจตารางชน + จัดตาราง (CP-SAT)   :8600
├── 07_rag_llm_engine/                # RAG ระเบียบ/หลักสูตร + LLM generate  :8700
├── 08_recommendation_feedback/       # คำแนะนำ + แจ้งเตือน + log + feedback  :8800
│      └── แต่ละโฟลเดอร์มี:
│          01_env.txt      = ใช้ภาษา/ไลบรารี/env อะไร
│          02_step.txt     = ทำอะไรก่อนหลัง (build order)
│          03_process.txt  = สถาปัตยกรรมภายใน + contract + ข้อควรระวัง
│
├── infra/                            # db init, prometheus config
├── data/                             # ข้อมูลดิบ/ที่ทำความสะอาดแล้ว (ไม่ขึ้น git)
├── docker-compose.yml
├── .env.example
└── Makefile
```

---

## เริ่มใช้งาน

```bash
git clone <repo-url>
cd ProJ-RMUTT-Planner

# 1. ตั้งค่า env
cp .env.example .env
#    แก้ .env ใส่ POSTGRES_PASSWORD, JWT_SECRET, LLM_API_KEY

# 2. รันทั้งระบบ
docker compose up -d --build

# 3. เช็คว่าขึ้นครบ
docker compose ps
curl http://localhost:8000/health
```

เปิดใช้งาน:
- หน้าเว็บ → http://localhost:3000
- API docs → http://localhost:8000/docs
- Qdrant → http://localhost:6333/dashboard

ออปชันเสริม:
```bash
docker compose --profile local-ai up -d      # โมเดลในเครื่อง (Ollama)
docker compose --profile monitoring up -d    # Prometheus + Grafana (:3001)
```

---

## หลักการออกแบบที่ทีมต้องยึด

1. **LLM ไม่ตัดสินเรื่องเวลา** — "ชน/ไม่ชน" คำนวณด้วยโค้ดใน `06` เท่านั้น
   LLM มีหน้าที่แค่ *อธิบาย* ผลลัพธ์ เพราะโมเดลภาษาคำนวณเวลาพลาดบ่อย
2. **ไม่มีหลักฐาน = ไม่ตอบ** — คำถามเรื่องระเบียบต้องผ่าน RAG และแนบแหล่งอ้างอิงเสมอ
3. **1 โมดูล = 1 container = 1 คนดูแล** — ตกลง contract ให้นิ่งก่อนเขียนโค้ด
4. **PDPA** — รหัสนักศึกษาเก็บเป็น hash ใน log, เกรด/ทรานสคริปต์เข้ารหัส,
   mask ข้อมูลส่วนตัวก่อนส่งให้ LLM บนคลาวด์

---

## นำเข้าข้อมูลจริงจากระบบทะเบียน (oreg3.rmutt.ac.th)

ระบบทะเบียนต้องล็อกอิน และ **โปรเจกต์นี้ไม่เก็บ/ไม่กรอกรหัสผ่านของใคร** — นักศึกษาล็อกอินเอง แล้วเซฟหน้าเป็น HTML

| หน้าในระบบทะเบียน | เซฟเป็น | parser |
|---|---|---|
| ตรวจสอบจบ (`graduate_check.asp`) | `data/raw/oreg/graduate_check_<id>.html` | `05_data_integration/src/graduate_check.py` |
| ค้นหารายวิชา → ผลค้นหา | `data/raw/oreg/search_<เทอม>.html` | `04_course_data_services/src/adapters/oreg_rmutt.py` |
| รายละเอียดรายวิชา (กลุ่ม/เวลา/สอบ) | `data/raw/oreg/course_<รหัส>.html` | `04_course_data_services/src/adapters/oreg_rmutt.py` |

```bash
# 1) ดูว่าเหลือกี่หน่วยกิต หมวดไหนยังไม่ผ่าน วิชาไหนต้องลงใหม่
cd 05_data_integration
python -m src.graduate_check ../data/raw/oreg/graduate_check_xxx.html

# 2) รวมกับวิชาที่เปิดเทอมนี้ → รายการที่ควรลง (ส่งต่อให้ 06 จัดตาราง)
python -m src.degree_plan ../data/raw/oreg/graduate_check_xxx.html ../data/raw/oreg/search_1-2569.html
```

ทดสอบ parser กับ fixture (สร้างจากภาพหน้าจอ):
```bash
cd 04_course_data_services && python -c "from src.adapters.oreg_rmutt import *; print(len(parse_search_results(open('tests/fixtures/search_results_sample.html','rb').read())))"
```

## ทำงานเป็นทีม

อ่าน [CONTRIBUTING.md](CONTRIBUTING.md) ก่อนเริ่ม — branch ต่อโมดูล, PR + review, CI รัน `pytest` ทุกโมดูล + เช็ค compose + กัน secret หลุด อัตโนมัติ
(workflow อยู่ที่ `.github/workflows/ci.yml` ใน root ของ repo)

## สถานะปัจจุบัน

🟡 **โครงร่าง + parser ข้อมูลจริง** — service ยังไม่มี logic แต่ท่อข้อมูลจากระบบทะเบียนใช้ได้แล้ว
- ✅ parser ค้นหารายวิชา / รายละเอียดวิชา / ตรวจสอบจบ (ผ่านทดสอบกับ fixture)
- ✅ `degree_plan.py` รวม "เหลืออะไร" + "เทอมนี้เปิดอะไร" → รายการวิชาที่ควรลง
- ⏳ fixture ยังสร้างจากภาพหน้าจอ — ต้องเอา HTML จริงมาแทนแล้วปรับ selector
- ⏳ ทุก service มี `/health` และ Dockerfile รอเติมโค้ดตาม `02_step.txt`

ลำดับที่ควรทำต่อ → ดู Sprint Plan ท้ายไฟล์ [`00_docs/03_flow.md`](00_docs/03_flow.md)

---

## ⚠️ ข้อจำกัดที่ต้องบอกผู้ใช้

> ระบบนี้เป็นเครื่องมือ **ช่วยวางแผนเบื้องต้น** ไม่ใช่การยืนยันจากมหาวิทยาลัย
> โปรดตรวจสอบกับระบบทะเบียนและอาจารย์ที่ปรึกษาก่อนลงทะเบียนจริงทุกครั้ง

ข้อมูลรายวิชา/ตารางสอนต้อง **ขอจากสำนักส่งเสริมวิชาการและงานทะเบียน (สวท.)** เป็นไฟล์
ค่าเริ่มต้นของระบบปิดการ scraping ไว้ (`ALLOW_SCRAPING=false`) — เปิดได้ต่อเมื่อได้รับอนุญาตแล้วเท่านั้น
