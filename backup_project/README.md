# สำรองงานทั้งหมด — RMUTT Study Planner

โฟลเดอร์นี้รวมเอกสารส่งงานและสรุปผลงานของทุกคนไว้ที่เดียว
ไฟล์ทั้งหมดสร้างจากข้อมูลในรีโปนี้เอง ตรวจย้อนได้ทุกตัวเลข

- คอมมิตทั้งหมด **81** ครั้ง (รวม merge 8 ครั้ง)
- ผู้ร่วมพัฒนา **8** คน
- สาขาที่ใช้พัฒนา **15** สาขา
- ช่วงเวลาทำงาน **15 กรกฎาคม 2569 – 23 กันยายน 2569**

สร้างใหม่เมื่อประวัติเปลี่ยน: `python ProJ-RMUTT-Planner/scripts/build_backup.py`

## ไฟล์ในโฟลเดอร์นี้

| ไฟล์ | เนื้อหา |
|---|---|
| `01_สถาปัตยกรรมระบบทั้งหมด.pdf` | ภาพรวม 9 โมดูล Use Case มายด์แมป ลำดับการทำงาน |
| `02_สไลด์บทที่7-RAG-LLM.pdf` | สไลด์ 16:9 เรื่องการค้นคืนเอกสารและ LLM |
| `03_เดโมเปิดในเบราว์เซอร์ได้เลย.html` | ไฟล์เดียวจบ ดับเบิลคลิกใช้งานได้ ไม่ต้องติดตั้งอะไร |
| `ประวัติการพัฒนา.html` | ตารางเต็ม คอมมิตทุกครั้ง แยกตามคนและเดือน |

## ผลงานรายบุคคล

| ผู้พัฒนา | คอมมิต | บรรทัดที่เพิ่ม | บรรทัดที่ลบ | ไฟล์ที่แก้ | ช่วงเวลาที่ทำงาน |
|---|---:|---:|---:|---:|---|
| Onpreyaq5 | 38 | +58,942 | -13,485 | 287 | 2026-08-07 – 2026-09-23 |
| Nuthaluek kokotsomrong | 14 | +9,667 | -1,086 | 52 | 2026-07-15 – 2026-09-23 |
| fffalafair | 5 | +14,284 | -12,879 | 186 | 2026-09-20 – 2026-09-22 |
| Phanlop Boonluea | 5 | +14,879 | -514 | 211 | 2026-09-21 – 2026-09-22 |
| cheewakorn | 5 | +4,552 | -725 | 37 | 2026-09-21 – 2026-09-22 |
| Marisa Pimpralab | 3 | +2,159 | -237 | 35 | 2026-09-20 – 2026-09-22 |
| DevnameJay | 2 | +2,628 | -20 | 15 | 2026-09-20 – 2026-09-22 |
| Saran Thanyawikai | 1 | +18,358 | -15 | 53 | 2026-09-22 – 2026-09-22 |

> นับเฉพาะคอมมิตที่ไม่ใช่ merge · จำนวนบรรทัดรวมไฟล์ที่เครื่องมือสร้างให้ด้วย
> จึงควรดูประกอบกับจำนวนคอมมิตและโมดูลที่รับผิดชอบ

## ใครทำโมดูลไหน

**Onpreyaq5** — 09 แอปรวม (94), 07 RAG + LLM (89), ใบงาน LAB (89), 02 API / Backend (26), 03 AI Router / Agent (23)

**Nuthaluek kokotsomrong** — 09 แอปรวม (39), หน้าเว็บเอกสาร (7), 07 RAG + LLM (3), เอกสารประกอบ (2), สคริปต์ตรวจสอบ (1)

**fffalafair** — 02 API / Backend (393)

**Phanlop Boonluea** — 02 API / Backend (182), 03 AI Router / Agent (18), 04 ข้อมูลรายวิชา (4), เอกสารประกอบ (1), 09 แอปรวม (1)

**cheewakorn** — 06 ตรวจตารางชน / จัดตาราง (50)

**Marisa Pimpralab** — 08 สถิติและความเห็น (47)

**DevnameJay** — 05 ข้อมูลนักศึกษา (19)

**Saran Thanyawikai** — 01 หน้าเว็บผู้ใช้ (53)

## ความเคลื่อนไหวรายเดือน

| เดือน | คอมมิต | ผู้พัฒนา |
|---|---:|---|
| กรกฎาคม 2569 | 3 | Nuthaluek kokotsomrong (3) |
| สิงหาคม 2569 | 3 | Onpreyaq5 (3) |
| กันยายน 2569 | 67 | Onpreyaq5 (35), Nuthaluek kokotsomrong (11), fffalafair (5), Phanlop Boonluea (5), cheewakorn (5), Marisa Pimpralab (3), DevnameJay (2), Saran Thanyawikai (1) |

## สาขาที่ใช้พัฒนา

- `develop`
- `docs/architecture-page`
- `docs/onboarding`
- `feat/api-backend`
- `feat/data-integration`
- `feat/docker-runnable`
- `feat/feedback`
- `feat/gemini-proxy-and-pdf`
- `feat/github-pages-demo`
- `feat/rag-in-browser`
- `feat/schedule-enging`
- `feat/web-app`
- `fix/09-security-ux-audit`
- `main`
- `merge/all-modules`

## การรวมงานเข้าสาขาหลัก

| วันที่ | ผู้รวม | รายละเอียด |
|---|---|---|
| 2026-09-23 | Onpreyaq5 | merge feat/web-app |
| 2026-09-23 | Onpreyaq5 | merge feat/data-integration |
| 2026-09-23 | Onpreyaq5 | merge feat/schedule-enging |
| 2026-09-23 | Onpreyaq5 | merge feat/api-backend |
| 2026-09-23 | Onpreyaq5 | merge develop |
| 2026-09-23 | Onpreyaq5 | merge feat/feedback |
| 2026-09-23 | Marisa Pimpralab | Merge branch 'main' into feat/feedback |
| 2026-09-22 | Marisa Pimpralab | Merge branch 'develop' into feat/feedback |

---

เอกสารระเบียบ หลักสูตร ปฏิทินการศึกษา และตารางสอนในระบบนี้
**เป็นข้อมูลจำลองสำหรับต้นแบบ** ไม่ใช่ข้อมูลจริงของมหาวิทยาลัย
