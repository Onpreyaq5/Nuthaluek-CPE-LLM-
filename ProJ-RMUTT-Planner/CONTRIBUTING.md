# วิธีทำงานร่วมกันในทีม (ทำงานตรงบน main)

> ทีมตกลงให้ทุกคนทำงานบน `main` โดยแบ่งความรับผิดชอบตามโฟลเดอร์ ไม่ต้องสร้าง Branch หรือ Pull Request

## 1. เริ่มต้นครั้งแรก

```bash
git clone https://github.com/Onpreyaq5/Nuthaluek-CPE-LLM-.git
cd Nuthaluek-CPE-LLM-/ProJ-RMUTT-Planner
cp .env.example .env
```

ห้าม commit ไฟล์ `.env`, API key, รหัสผ่าน หรือข้อมูลนักศึกษาจริง

## 2. ขอบเขตการทำงาน

| พื้นที่ | ผู้รับผิดชอบ |
|---|---|
| `00_docs/` | เอกสารกลาง — แก้เมื่อทีมตกลงร่วมกัน |
| `01_web_app/` | เจ้าของโมดูล Web/UI |
| `02_api_backend/` | เจ้าของโมดูล API/Auth |
| `03_ai_router_agent/` | เจ้าของโมดูล AI Router |
| `04_course_data_services/` | เจ้าของโมดูลข้อมูลรายวิชา |
| `05_data_integration/` | เจ้าของโมดูลเชื่อมและทำความสะอาดข้อมูล |
| `06_schedule_conflict_engine/` | เจ้าของโมดูลตรวจตารางชน |
| `07_rag_llm_engine/` | เจ้าของโมดูล RAG/LLM |
| `08_recommendation_feedback/` | เจ้าของโมดูลคำแนะนำและ Feedback |
| `09_main_app/` | **เฟิสเท่านั้น — พื้นที่รวมแอปหลัก** |
| `docker-compose.yml`, `Makefile`, `.env.example`, `infra/` | **เฟิสเท่านั้น — ไฟล์เชื่อมระบบ** |

**กติกาหลัก:** สมาชิกแก้เฉพาะโฟลเดอร์ของตัวเอง ห้ามย้าย ลบ หรือแก้ไฟล์ของคนอื่น หากจำเป็นต้องเปลี่ยน contract ระหว่างโมดูลให้คุยกับเจ้าของโฟลเดอร์และเฟิสก่อน

## 3. รอบการทำงานประจำวัน

ก่อนเริ่มแก้ทุกครั้ง:

```bash
git checkout main
git pull origin main
```

เมื่อทำเสร็จ ให้ add เฉพาะโฟลเดอร์ของตัวเอง ตัวอย่างโมดูล 06:

```bash
git add 06_schedule_conflict_engine/
git commit -m "[06] อธิบายสิ่งที่แก้"
git pull --rebase origin main
git push origin main
```

รูปแบบ commit message: `[หมายเลขโมดูล] ทำอะไร` เช่น `[04] แก้ parser ให้รองรับวิชาออนไลน์`

## 4. ก่อน push เช็ก

- ทดสอบโค้ดในโฟลเดอร์ตัวเองแล้ว
- อัปเดต `01_env.txt`, `02_step.txt` หรือ `03_process.txt` หากพฤติกรรมเปลี่ยน
- ไม่มี `.env`, API key, รหัสผ่าน หรือข้อมูลนักศึกษาจริง
- `git status` ไม่มีไฟล์จากโฟลเดอร์ของคนอื่นติดมาด้วย
- ดึง `main` ล่าสุดก่อน push แล้ว

## 5. ถ้า push ไม่ผ่านหรือโค้ดชนกัน

1. ห้ามใช้ `git push --force`
2. รัน `git pull --rebase origin main`
3. หากเกิด conflict ในโฟลเดอร์ของตัวเอง ให้แก้แล้วทดสอบใหม่
4. หาก conflict อยู่ใน `09_main_app` หรือไฟล์ส่วนกลาง ให้หยุดและแจ้งเฟิส

## 6. การรวมแอป

เฟิสเป็นผู้ตรวจงานจาก `01–08` และรวมให้ทำงานจริงใน `09_main_app` รวมถึงดูแล `docker-compose.yml`, `Makefile`, `.env.example` และ `infra/`

GitHub ไม่ได้บล็อกสิทธิ์เป็นรายโฟลเดอร์ กติกานี้เป็นข้อตกลงของทีม ทุกคนที่มีสิทธิ์ Write ต้องรับผิดชอบไม่แก้พื้นที่นอกหน้าที่ของตนเอง
