# 04 — แบ่งงานในทีม (Team Roles)

หลักการ: **1 โฟลเดอร์ = 1 เจ้าของ = 1 branch** → merge ไม่ชนกัน

| โมดูล | ผู้รับผิดชอบ | ทักษะที่ใช้ | branch |
|---|---|---|---|
| `01_web_app` | | React/Next.js, UI/UX | `feat/web-app` |
| `02_api_backend` | | FastAPI, Postgres, Auth | `feat/api-backend` |
| `03_ai_router_agent` | | Prompt, Agent, LLM API | `feat/ai-router` |
| `04_course_data_services` | | Scraping/Parsing, Pandas | `feat/course-data` |
| `05_data_integration` | | Data cleaning, Graph, Algo | `feat/data-integration` |
| `06_schedule_conflict_engine` | | **อัลกอริทึม, OR-Tools** (คนแข็งสุดควรอยู่ตรงนี้) | `feat/schedule-engine` |
| `07_rag_llm_engine` | | RAG, Vector DB, Embedding | `feat/rag-llm` |
| `08_recommendation_feedback` | | Celery, Monitoring, Analytics | `feat/feedback` |
| DevOps / Docker / CI | | Docker, GitHub Actions | `chore/infra` |
| เอกสาร + รายงาน + สไลด์ | | เขียน, ทำ diagram | `docs/report` |

## กติกา Git ของทีม

```
main        ← โค้ดที่รันได้เสมอ (ห้าม push ตรง)
 └ dev      ← รวมงานทุกคน
    └ feat/<module>   ← แต่ละคนทำงานตรงนี้
```

- commit message: `[06] เพิ่มการตรวจสอบตารางสอบชน`
- เปิด Pull Request → ให้เพื่อนอย่างน้อย 1 คน review → merge เข้า dev
- ห้าม commit ไฟล์ `.env`, ข้อมูลนักศึกษาจริง, API key

## Definition of Done (แต่ละโมดูลถือว่าเสร็จเมื่อ)
1. `docker compose up <service>` ขึ้นได้ ไม่ error
2. `/health` ตอบ 200
3. มี unit test อย่างน้อย 3 เคส และผ่าน
4. อัปเดต `01_env.txt` / `02_step.txt` / `03_process.txt` ให้ตรงกับของจริง
5. มีตัวอย่าง request/response ใน README ของโมดูล
