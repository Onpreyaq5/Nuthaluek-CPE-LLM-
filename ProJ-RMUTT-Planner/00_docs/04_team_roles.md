# 04 — แบ่งงานในทีม (Team Roles)

หลักการ: **1 โฟลเดอร์ = 1 เจ้าของ** ทุกคนทำงานตรงบน `main` และห้ามแก้พื้นที่ของคนอื่น

| โฟลเดอร์ / งาน | ผู้รับผิดชอบ | ทักษะหลัก | สถานะ |
|---|---|---|---|
| `01_web_app/` | **เฟิส** | React, Next.js, UI/UX | ยังไม่เริ่ม |
| `02_api_backend/` | fffalafair | FastAPI, Postgres, Auth | มีโค้ดแล้ว (`feat/api-backend`) |
| `03_ai_router_agent/` | Automatic28m (Phanlop) | Prompt, Agent, LLM API | มีโค้ดแล้ว (`develop`) |
| `04_course_data_services/` | ยังไม่มีเจ้าของ | Parsing, Data services | มี parser ระบบทะเบียนบน `main` |
| `05_data_integration/` | DevnameJay | Data cleaning, Graph, Algorithm | มีโค้ดแล้ว (`feat/data-integration`) |
| `06_schedule_conflict_engine/` | **เฟิส** | Algorithm, OR-Tools | ยังไม่เริ่ม — งานสำคัญที่สุด |
| `07_rag_llm_engine/` | **ยังไม่มีเจ้าของ — รับสมัคร** | RAG, Vector DB, Embedding | ยังไม่เริ่ม (ติดที่ยังไม่มีไฟล์ระเบียบ PDF) |
| `08_recommendation_feedback/` | marisa46054 (Marisa) | Monitoring, Analytics, Feedback | มีโค้ดแล้ว (`feat/feedback`) |
| `09_main_app/` | **เฟิส** | รวมระบบและทดสอบแอปจริง | — |
| `docker-compose.yml`, `Makefile`, `.env.example`, `infra/` | **เฟิส** | Docker, Integration, CI | — |
| `00_docs/` | ทีมตกลงร่วมกัน | เอกสาร, Diagram, รายงาน | — |

> ชื่อในตารางดึงจากคนที่ commit จริงในแต่ละโมดูล ใครไม่ตรงให้แก้ได้เลย

## กติกา Git ของทีม

- ทุกคนใช้ branch `main` เดียวกัน ไม่ต้องสร้าง Branch หรือ Pull Request
- ก่อนเริ่มงานต้อง `git pull origin main`
- add และ commit เฉพาะโฟลเดอร์ของตัวเอง
- ก่อน push ให้ `git pull --rebase origin main`
- ห้าม `git push --force`
- ห้ามแก้ `09_main_app/` และไฟล์ส่วนกลางที่เฟิสดูแล
- หากจำเป็นต้องแก้ contract ข้ามโมดูล ต้องคุยกับเจ้าของทั้งสองฝั่งและเฟิสก่อน

## หน้าที่ของเฟิส

1. ตรวจงานจากโมดูล `01–08`
2. นำโมดูลมาประกอบใน `09_main_app`
3. ดูแลไฟล์เชื่อมระบบและ Docker
4. ทดสอบว่าแอปหลักรันร่วมกันได้จริง
5. ตัดสินใจเมื่อมี conflict ระหว่างโมดูล
6. รับผิดชอบ `06_schedule_conflict_engine` (ตรรกะตารางชน) และ `01_web_app` (หน้าเดโม่) เพิ่ม

## งานที่ยังไม่มีคนรับ

| โมดูล | ทำไมสำคัญ | ต้องเริ่มจาก |
|---|---|---|
| `07_rag_llm_engine/` | ตอบคำถามระเบียบพร้อมอ้างอิง — เป็นส่วนที่ตรงกับวิชา LLM มากที่สุด | หาไฟล์ PDF ระเบียบ/คู่มือนักศึกษา/มคอ.2 ก่อน |
| `04_course_data_services/` | ดึงข้อมูลรายวิชาจริงจากระบบทะเบียน | มี parser อยู่แล้วบน `main` เหลือทำเป็น service |

## สิ่งที่ต้องทำร่วมกันเร็ว ๆ นี้

1. **นัดวันรวมงาน** — ตอนนี้โค้ดกระจายอยู่ 4 ที่ (`main`, `develop`, `feat/api-backend`,
   `feat/data-integration`, `feat/feedback`) ยัง `docker compose up` ทั้งระบบไม่ได้
2. ตกลงว่าจะรวมที่ `main` หรือ `develop`
3. `02_api_backend` ถูกถอดออกจาก `main` ไปแล้ว ต้องเอากลับเข้ามาตอนรวม

## Definition of Done

1. Service ของโมดูลเริ่มทำงานได้โดยไม่ error
2. `/health` ตอบ 200 หากโมดูลมี API
3. มี test และ test ผ่าน
4. เอกสาร `01_env.txt`, `02_step.txt`, `03_process.txt` ตรงกับโค้ดจริง
5. ไม่มี secret หรือข้อมูลนักศึกษาจริงใน commit
6. เฟิสสามารถนำโมดูลไปรวมกับแอปหลักได้
