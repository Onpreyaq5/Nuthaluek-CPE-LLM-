# 04 — แบ่งงานในทีม (Team Roles)

หลักการ: **1 โฟลเดอร์ = 1 เจ้าของ** ทุกคนทำงานตรงบน `main` และห้ามแก้พื้นที่ของคนอื่น

| โฟลเดอร์ / งาน | ผู้รับผิดชอบ | ทักษะหลัก |
|---|---|---|
| `01_web_app/` | เติมชื่อ/GitHub | React, Next.js, UI/UX |
| `02_api_backend/` | เติมชื่อ/GitHub | FastAPI, Postgres, Auth |
| `03_ai_router_agent/` | เติมชื่อ/GitHub | Prompt, Agent, LLM API |
| `04_course_data_services/` | เติมชื่อ/GitHub | Parsing, Data services |
| `05_data_integration/` | เติมชื่อ/GitHub | Data cleaning, Graph, Algorithm |
| `06_schedule_conflict_engine/` | เติมชื่อ/GitHub | Algorithm, OR-Tools |
| `07_rag_llm_engine/` | เติมชื่อ/GitHub | RAG, Vector DB, Embedding |
| `08_recommendation_feedback/` | เติมชื่อ/GitHub | Monitoring, Analytics, Feedback |
| `09_main_app/` | **เฟิส** | รวมระบบและทดสอบแอปจริง |
| `docker-compose.yml`, `Makefile`, `.env.example`, `infra/` | **เฟิส** | Docker, Integration, CI |
| `00_docs/` | ทีมตกลงร่วมกัน | เอกสาร, Diagram, รายงาน |

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

## Definition of Done

1. Service ของโมดูลเริ่มทำงานได้โดยไม่ error
2. `/health` ตอบ 200 หากโมดูลมี API
3. มี test และ test ผ่าน
4. เอกสาร `01_env.txt`, `02_step.txt`, `03_process.txt` ตรงกับโค้ดจริง
5. ไม่มี secret หรือข้อมูลนักศึกษาจริงใน commit
6. เฟิสสามารถนำโมดูลไปรวมกับแอปหลักได้
