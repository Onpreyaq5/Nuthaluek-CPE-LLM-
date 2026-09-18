# วิธีทำงานร่วมกันในทีม (CONTRIBUTING)

> อ่านหน้านี้ 5 นาทีก่อนแตะโค้ด — จะได้ไม่ทับงานกันและ merge ไม่พัง

## 1. เริ่มต้นครั้งแรก

```bash
git clone https://github.com/Onpreyaq5/Nuthaluek-CPE-LLM-.git
cd Nuthaluek-CPE-LLM-/ProJ-RMUTT-Planner
cp .env.example .env          # ใส่ค่าจริงของตัวเอง ห้าม commit ไฟล์นี้
```

Windows: ถ้าเจอ `Filename too long` ให้รัน `git config --global core.longpaths true`

## 2. ใครทำโฟลเดอร์ไหน

1 โฟลเดอร์ = 1 เจ้าของ = 1 branch — ดูตารางใน [`00_docs/04_team_roles.md`](00_docs/04_team_roles.md) แล้ว**เติมชื่อตัวเอง**ลงไป

| โฟลเดอร์ | branch ของคุณ |
|---|---|
| `01_web_app` | `feat/web-app` |
| `02_api_backend` | `feat/api-backend` |
| `03_ai_router_agent` | `feat/ai-router` |
| `04_course_data_services` | `feat/course-data` |
| `05_data_integration` | `feat/data-integration` |
| `06_schedule_conflict_engine` | `feat/schedule-engine` |
| `07_rag_llm_engine` | `feat/rag-llm` |
| `08_recommendation_feedback` | `feat/feedback` |
| `00_docs` / README | `docs/<เรื่อง>` |
| docker / CI | `chore/<เรื่อง>` |

**กติกาสำคัญ:** แก้ได้เฉพาะโฟลเดอร์ของตัวเอง ถ้าต้องแก้ของคนอื่น (เช่น เปลี่ยน contract ใน `03_process.txt`) ให้เปิด Issue คุยก่อน

## 3. รอบการทำงานประจำวัน

```bash
git checkout main && git pull            # เอาของใหม่สุดมาก่อนเสมอ
git checkout -b feat/schedule-engine     # (ครั้งแรก) หรือ git checkout feat/schedule-engine
# ... เขียนโค้ด ...
git add 06_schedule_conflict_engine/     # add เฉพาะโฟลเดอร์ตัวเอง
git commit -m "[06] เพิ่มการตรวจสอบตารางสอบชน"
git push -u origin feat/schedule-engine
```

แล้วไปเปิด **Pull Request** บน GitHub → เลือก base = `main`
→ ให้เพื่อน 1 คน review → CI เขียวแล้วค่อยกด **Squash and merge**

รูปแบบ commit message: `[หมายเลขโมดูล] ทำอะไร` เช่น `[04] แก้ parser ให้รองรับวิชาออนไลน์`

## 4. ก่อนเปิด PR เช็ค 4 ข้อ

- [ ] `docker compose build <service>` ผ่าน
- [ ] `pytest` ในโฟลเดอร์ตัวเองผ่าน (`cd 0X_xxx && pip install -r requirements.txt pytest && pytest`)
- [ ] อัปเดต `01_env.txt` / `02_step.txt` / `03_process.txt` ถ้าของจริงเปลี่ยนไปจากที่เขียนไว้
- [ ] ไม่มี `.env`, API key, หรือข้อมูลนักศึกษาจริง (รหัส/ชื่อ/เกรด) ติดไปใน commit

## 5. ห้ามเด็ดขาด

- `git push origin main` ตรง ๆ (main รับได้เฉพาะจาก PR)
- `git push --force` บน branch ที่มีคนอื่นใช้
- commit ไฟล์ HTML ที่เซฟจากระบบทะเบียนของตัวเอง (มีชื่อ-รหัส-เกรด) → วางไว้ใน `data/raw/` ซึ่ง `.gitignore` กันไว้แล้ว
- ใส่รหัสผ่านระบบทะเบียนลงในโค้ด/config/แชท

## 6. ถ้า merge แล้วชนกัน (conflict)

```bash
git checkout feat/xxx
git fetch origin
git merge origin/main        # แก้ไฟล์ที่ขึ้น <<<<<<< >>>>>>> แล้ว
git add . && git commit
git push
```

ชนกันบ่อย = มีคน 2 คนแก้ไฟล์เดียวกัน → กลับไปดูข้อ 2

## 7. ช่องทางคุยงาน

- เรื่องโค้ด/บั๊ก → GitHub **Issues** (ติด label ตามโมดูล)
- เรื่อง contract ระหว่างโมดูล → Issue + แท็กเจ้าของทั้ง 2 ฝั่ง
- ประชุมทีม → อัปเดตความคืบหน้าใน `00_docs/03_flow.md` ท้ายตาราง Sprint Plan
