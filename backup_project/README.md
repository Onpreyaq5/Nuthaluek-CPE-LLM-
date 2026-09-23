# สำรองงานทั้งหมด — RMUTT Study Planner

ระบบวางแผนการเรียน มหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี

## เปิดใช้งานระบบจริง

| เปิดอะไร | ลิงก์ |
|---|---|
| แอปหลัก (09) — จัดตาราง ตรวจตารางชน ถามระเบียบ ไม่ต้องเข้าสู่ระบบ | https://scientific-trips-recognize-sight.trycloudflare.com |
| หน้าเว็บ CampusMate (01) — ระบบเต็ม เข้าสู่ระบบ admin / admin1234 | https://eclipse-formatting-retired-montgomery.trycloudflare.com |
| หน้าเว็บ CampusMate (01) — ชุดเดิม | https://broadband-potter-primary-guestbook.trycloudflare.com |
| Grafana — กราฟเฝ้าดูระบบ เปิดดูได้โดยไม่ต้องเข้าสู่ระบบ | https://lane-liberty-increasing-hotel.trycloudflare.com |
| เอกสารทั้งหมดในรูปแบบเว็บ (GitHub Pages) | https://onpreyaq5.github.io/Nuthaluek-CPE-LLM-/ |

> ลิงก์ `trycloudflare.com` เป็นลิงก์ชั่วคราว ใช้ได้เฉพาะตอนเครื่องที่รัน Docker เปิดอยู่
> และเปลี่ยนใหม่ทุกครั้งที่สั่งขึ้น ถ้าเปิดไม่ได้ให้รันระบบเองตามหัวข้อด้านล่าง

## รันระบบเองด้วย Docker

```bash
cd ProJ-RMUTT-Planner
cp .env.example .env
docker compose up -d --build        # เปิด http://localhost:3000
bash scripts/verify_docker.sh       # ตรวจทุกบริการว่าทำงานจริง
```

หน้าเว็บ CampusMate ตัวเต็มพร้อมทุกบริการที่เรียกใช้:

```bash
docker compose -f deploy/webapp/docker-compose.yml --env-file .env up -d --build
python deploy/webapp/verify.py      # เปิด http://localhost:4001
```

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | เนื้อหา |
|---|---|
| `01_สถาปัตยกรรมระบบทั้งหมด.pdf` | ภาพรวม 9 โมดูล Use Case มายด์แมป ลำดับการทำงาน |
| `02_สไลด์บทที่7-RAG-LLM.pdf` | สไลด์ 16:9 เรื่องการค้นคืนเอกสารและ LLM |
| `03_เดโมเปิดในเบราว์เซอร์ได้เลย.html` | ไฟล์เดียวจบ ดับเบิลคลิกใช้งานได้ ไม่ต้องติดตั้งอะไร |
| `ประวัติการพัฒนา.html` · `.pdf` | ผลงานรายคน ใครทำโมดูลไหน และคอมมิตทุกรายการ |
| `โปรเจกต์ทั้งหมด.zip` | สำเนาโค้ดทั้งโปรเจกต์ ไม่มี node_modules ไม่มีคีย์ |
| `ประวัติ-git-ทั้งหมด.bundle` | ประวัติ git ครบทุกคอมมิตทุกสาขา |

## กู้คืนจากไฟล์สำรอง

```bash
git clone ประวัติ-git-ทั้งหมด.bundle rmutt-planner   # ได้ประวัติครบทุกคน
unzip โปรเจกต์ทั้งหมด.zip                              # หรือเอาแค่ไฟล์
```

---

สร้างไฟล์ในโฟลเดอร์นี้ใหม่: `python ProJ-RMUTT-Planner/scripts/build_backup.py`
(83 คอมมิต · 8 คน · 15 สาขา · 15 กรกฎาคม 2569 – 23 กันยายน 2569)

เอกสารระเบียบ หลักสูตร ปฏิทินการศึกษา และตารางสอนในระบบนี้
**เป็นข้อมูลจำลองสำหรับต้นแบบ** ไม่ใช่ข้อมูลจริงของมหาวิทยาลัย
