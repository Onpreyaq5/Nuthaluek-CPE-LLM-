# 06 — Schedule Conflict & Auto-Planning Engine ⚙️
> **โมดูลหัวใจหลัก (Core Engine) ของระบบ RMUTT Study Planner**  
> ตรวจสอบตารางชน 100% Deterministic + จัดตารางอัตโนมัติด้วย Google OR-Tools CP-SAT  
> **ผู้รับผิดชอบ (Owner):** เฟิส  
> **Service Port:** `8600` | **Branch:** `feat/schedule-enging`

---

## 1. บทนำและที่มา: ทำไมต้องสร้างโมดูลนี้? (Problem Statement & Philosophy)

### ปัญหาที่พบในการจัดตารางเรียนของนักศึกษา (Pain Points)
การลงทะเบียนเรียนในแต่ละภาคการศึกษาของนักศึกษา มทร.ธัญบุรี มีความซับซ้อนสูงมากและมักเกิดข้อผิดพลาดที่ส่งผลเสียต่อการเรียน:
1. **เวลาเรียนชนกัน (Time Clash)**: รายวิชาบรรยายหรือปฏิบัติการของต่างหมวดวิชามีเวลาคาบเกี่ยวกัน แม้เพียง 30 นาทีก็ทำให้ลงทะเบียนไม่ได้
2. **เวลาสอบชนกัน (Exam Clash)**: แม้เวลาเรียนไม่ชน แต่วันและเวลาสอบกลางภาคหรือปลายภาคตรงกัน ส่งผลให้ไม่สามารถเข้าสอบได้ทั้งสองวิชา
3. **ติดเงื่อนไขวิชาบังคับก่อน (Prerequisite Fail)**: ลงทะเบียนวิชาต่อเนื่องโดยยังไม่ผ่านวิชาบังคับก่อนหน้า ทำให้ถูกถอนรายวิชาในภายหลัง
4. **หน่วยกิตเกิน/ต่ำกว่าเกณฑ์ (Credit Limit Exceeded/Under)**: ระเบียบ มทร.ธัญบุรี กำหนดภาคการศึกษาปกติลงทะเบียนได้ 9 – 21 หน่วยกิต (ภาคฤดูร้อนไม่เกิน 9 หน่วยกิต)
5. **ลงทะเบียนซ้ำซ้อน (Duplicate Section / Passed Course)**: ลงวิชาเดียวกันมากกว่า 1 กลุ่ม หรือลงวิชาที่เคยได้เกรดผ่านไปแล้ว
6. **ที่นั่งเต็ม (Seat Full)**: กลุ่มเรียนที่เลือกมีผู้ลงทะเบียนเต็มจำนวนแล้ว
7. **ตารางเรียนส่งผลเสียต่อคุณภาพชีวิต (Bad Schedule Quality)**: เรียนติดต่อกันเช้าจรดเย็นไม่มีเวลาพักกลางวัน, ช่องว่างรอเรียนนานเกิน 4 ชั่วโมง, หรือต้องวิ่งย้ายอาคารเรียนคนละฝั่งในเวลาไม่ถึง 15 นาที

### ปรัชญาการออกแบบ: "ทำไมระบบนี้ต้องไม่มี LLM ในส่วนคำนวณ?"
> **"LLM ไม่ตัดสินเรื่องเวลา — ชน/ไม่ชน คำนวณด้วยโค้ด 100% Deterministic เท่านั้น"**

Large Language Models (LLMs) เป็นโมเดลเชิงสถิติ (Probabilistic) ซึ่งมีความสามารถในการเข้าใจบริบทและภาษาธรรมชาติได้ดีเยี่ยม **แต่คำนวณตัวเลข ขอบเขตเวลา และเงื่อนไขตรรกะแบบแม่นยำสูง (Strict Constraints) ผิดพลาดบ่อยครั้ง (Hallucination)**
- หากให้ LLM ตัดสินว่าตารางชนหรือไม่ ความเสี่ยงที่นักศึกษาจะได้ตารางที่ชนกันจริงสูงเกินกว่าจะยอมรับได้
- **โมดูล 06 จึงถูกออกแบบให้เป็น Pure Mathematical & Rule-based Engine** ให้ผลลัพธ์ที่ถูกต้อง 100% และตรวจสอบซ้ำได้ (Reproducible) เสมอ
- จากนั้นโมดูล 06 จะส่งข้อมูลโครงสร้างเหตุผล (Structured Reason Data) ไปให้โมดูล `07_rag_llm_engine` เพื่อให้ LLM ทำหน้าที่เฉพาะสิ่งที่มันถนัดที่สุด นั่นคือ **"การอธิบายผลลัพธ์เป็นภาษาพูดที่เป็นมิตรกับมนุษย์"**

---

## 2. สถาปัตยกรรมและเทคโนโลยีหลัก (Technical Architecture)

```
                       ┌────────────────────────────────────────────────────────┐
                       │             06_schedule_conflict_engine                │
                       │                                                        │
[01 Web App] ─────────▶│  [FastAPI Endpoints :8600]                             │
[02 API Gateway] ─────▶│   ├── POST /conflicts/check & /validate                │
[03 AI Router] ───────▶│   ├── POST /conflicts/preview  (<50ms drag & drop)     │
                       │   ├── POST /plan/generate & /plans/auto                │
                       │   ├── POST /plan/repair                                │
                       │   └── POST /plan/compare                               │
                       │                         │                              │
                       │                         ▼                              │
                       │  ┌──────────────────────────────────────────────────┐  │
                       │  │               CORE ENGINE LAYER                  │  │
                       │  │                                                  │  │
                       │  │  1. 182-Bitmask Engine                           │  │
                       │  │     - 7 Days x 26 Slots (30-min)                 │  │
                       │  │     - O(1) Bitwise Collision Check (mask_a & b)  │  │
                       │  │     - Overlap Interval Decoder                   │  │
                       │  │                                                  │  │
                       │  │  2. Conflict Detector (C1 - C6)                  │  │
                       │  │     - Time / Exam / Prereq / Credit / Dup / Seat │  │
                       │  │                                                  │  │
                       │  │  3. Quality-of-Life Evaluator (W1 - W5)          │  │
                       │  │     - Stretch / Large Gap / Rush Move / Days     │  │
                       │  │                                                  │  │
                       │  │  4. Google OR-Tools CP-SAT Solver                │  │
                       │  │     - Boolean Decision Variables x[s]            │  │
                       │  │     - Multi-Objective Optimization               │  │
                       │  │     - Solution Pool (3-5 Diverse Plans)          │  │
                       │  │     - 3-Tier Relaxation Fallback                 │  │
                       │  │                                                  │  │
                       │  │  5. Plan Repair Engine                           │  │
                       │  │     - Alternative Non-Conflicting Section Swap   │  │
                       │  └──────────────────────────────────────────────────┘  │
                       └────────────────────────────────────────────────────────┘
```

### 1. ระบบ 182-Bitmask Collision Math ($O(1)$)
- **มิติเวลา**: 1 สัปดาห์มี 7 วัน (วันจันทร์=0 ถึง วันอาทิตย์=6)
- **ช่วงเวลาเรียน**: 08:00 ถึง 21:00 น. รวม 13 ชั่วโมงต่อวัน
- **ความละเอียดของสล็อต**: ช่องละ 30 นาที $\rightarrow$ 26 ช่องต่อวัน
- **จำนวนบิตรวม**: $7 \times 26 = 182$ บิต (จัดเก็บในรูป Python Large Integer / Bitfield)
- **การตรวจเวลาชน**:
  $$\text{Clash}(A, B) \iff (\text{mask}_A \ \& \ \text{mask}_B) \ne 0$$
  มีความเร็วในการประมวลผลระดับ Nanoseconds ($O(1)$)
- **การถอดรหัส (Overlap Decoding)**:
  นำบิตที่ซ้อนทับกันมาคำนวณกลับเป็นวัน และเวลาเริ่มต้น-สิ้นสุด เช่น `จันทร์ 09:00 - 10:30` เพื่อส่งต่อให้ผู้ใช้และโมดูล LLM

### 2. Google OR-Tools CP-SAT Auto Planner
การจัดตารางเรียนเป็นปัญหาประเภท **Combinatorial Optimization (NP-hard)** เราจึงเลือกใช้ **Google OR-Tools CP-SAT Solver** แทนการใช้วิธีสุ่มหรือ Greedy Search:
- **ตัวแปรตัดสินใจ (Decision Variable)**: $x_s \in \{0, 1\}$ แทนการเลือกลง Section $s$
- **Hard Constraints**:
  - เลือกได้ไม่เกิน 1 กลุ่มต่อวิชา: $\sum_{s \in S_c} x_s \le 1$
  - ห้ามเวลาเรียนหรือเวลาสอบชนกัน: $x_u + x_v \le 1 \quad \forall (u, v) \in \text{Clashes}$
  - หน่วยกิตรวมอยู่ในช่วงที่กำหนด: $\text{MinCredits} \le \sum credits(s) \cdot x_s \le \text{MaxCredits}$
  - ผ่านวิชาบังคับก่อนครบทุกตัว
- **ฟังก์ชันเป้าหมาย (Multi-Objective Maximization)**:
  $$\max \left( w_1 \cdot \text{PriorityScore} + w_2 \cdot \text{Preferences} - w_3 \cdot \text{DaysOnCampus} \right)$$
- **Solution Diversity**: ระบบเพิ่ม Constraint ตัดคำตอบเดิมออก เพื่อค้นหาแผนที่ดีที่สุดลำดับถัดไป ทำให้ได้ชุดทางเลือก 3 – 5 แผนที่ไม่ซ้ำกัน
- **ระบบผ่อนปรน 3 ระดับ (3-Tier Relaxation Fallback)**:
  หาก Solver หาคำตอบไม่ได้ (Infeasible เนื่องจากเงื่อนไขตึงเกินไป) ระบบจะไม่คืน Error เปล่า แต่จะผ่อนปรนตามลำดับ:
  1. *ผ่อนปรนความชอบ*: ยอมให้มีคาบเช้าหรือวันว่างน้อยลง
  2. *ผ่อนปรนที่นั่ง*: ยอมให้เลือกกลุ่มที่ที่นั่งเต็ม พร้อมแนบคำแนะนำขอโควตา
  3. *ผ่อนปรนหน่วยกิต*: ลดเกณฑ์หน่วยกิตขั้นต่ำลง

---

## 3. รายละเอียดกฎการตรวจสอบ (Rules & Codes)

### กฎข้อผิดพลาดร้ายแรง (Hard Conflicts: C1 – C6)
| รหัส | ชื่อกฎ | คำอธิบาย | ระดับความรุนแรง |
|---|---|---|---|
| **C1** | `TIME_CLASH` | คาบเรียนมีเวลาทับซ้อนกันตั้งแต่ 30 นาทีขึ้นไป | `ERROR` |
| **C2** | `EXAM_CLASH` | วันและเวลาสอบกลางภาคหรือสอบปลายภาคตรงกัน | `ERROR` |
| **C3** | `PREREQ_FAIL` | ยังไม่ผ่านรายวิชาบังคับก่อนตามโครงสร้างหลักสูตร | `ERROR` |
| **C4** | `CREDIT_LIMIT` | หน่วยกิตรวมเกิน 21 (ปกติ) / เกิน 9 (ฤดูร้อน) หรือต่ำกว่า 9 | `ERROR` / `WARNING` |
| **C5** | `DUPLICATE` | ลงทะเบียนซ้ำ 2 กลุ่มในวิชาเดียวกัน หรือลงวิชาที่เคยผ่านแล้ว | `ERROR` |
| **C6** | `SEAT_FULL` | จำนวนผู้ลงทะเบียนในกลุ่มเต็มจำนวนที่เปิดรับ | `ERROR` |

### กฎคำเตือนคุณภาพชีวิต (Soft Rules: W1 – W5)
| รหัส | ชื่อกฎ | คำอธิบาย | ระดับความรุนแรง |
|---|---|---|---|
| **W1** | `LONG_STRETCH` | มีการเรียนติดต่อกันยาวนานเกิน 6 ชั่วโมงโดยไม่มีเวลาพัก | `WARNING` |
| **W2** | `LARGE_GAP` | มีช่องว่างรอเรียนระหว่างคาบในวันเดียวกันเกิน 4 ชั่วโมง | `WARNING` |
| **W3** | `EARLY_CLASS` | มีคาบเรียน 08:00 น. หรือมีเรียนในวันที่นักศึกษาขอว่างไว้ | `WARNING` |
| **W4** | `RUSH_MOVE` | ต้องเปลี่ยนอาคารเรียน/วิทยาเขตระหว่างคาบที่มีเวลาพักน้อยกว่า 15 นาที | `WARNING` |
| **W5** | `HEAVY_DAYS` | ตารางเรียนกระจายตัวจนต้องเดินทางมามหาวิทยาลัย 6 – 7 วัน/สัปดาห์ | `WARNING` |

---

## 4. รายละเอียดโครงสร้าง API (Endpoints Specification)

| Method | Endpoint | วัตถุประสงค์ | ความเข้ากันได้ |
|---|---|---|---|
| `GET` | `/health` | ตรวจสอบสถานะการทำงานของ Service | Docker Healthcheck, CI |
| `POST` | `/conflicts/check` | ตรวจสอบข้อขัดแย้ง C1-C6 และ W1-W5 แบบละเอียด | โมดูล 03 (`ai_router_agent`) |
| `POST` | `/validate` | Alias ของการตรวจตารางชน | โมดูล 02 (`api_backend`) |
| `POST` | `/conflicts/preview` | ตรวจเฉพาะ Bitmask Clash อย่างรวดเร็ว (< 50ms) | โมดูล 01 (`web_app` Drag & Drop) |
| `POST` | `/plan/generate` | จัดตารางเรียนอัตโนมัติ 3-5 แผนด้วย CP-SAT | สเปกกลางโมดูล 06 |
| `POST` | `/plans/auto` | Alias ของการจัดตารางอัตโนมัติ | โมดูล 03 (`ai_router_agent`) |
| `POST` | `/generate` | Alias ของการจัดตารางอัตโนมัติ | โมดูล 02 (`api_backend`) |
| `POST` | `/plan/repair` | วิเคราะห์ตารางที่ชนและเสนอ Section ทางเลือก | โมดูล 01, 02 |
| `POST` | `/plan/compare` | เปรียบเทียบความแตกต่างระหว่าง Plan A และ Plan B | โมดูล 01, 08 |

---

## 5. สรุปผลการทดสอบอย่างละเอียด (Test Suite Results)

ชุดการทดสอบพัฒนาด้วย **Pytest** ครอบคลุมทุกเลเยอร์ของระบบ:
- `test_bitmask.py`: ทดสอบการแปลงสล็อตบิต, การชนหัวท้าย, การทับซ้อน, คาบคร่อมเที่ยง, และการคำนวณโปรไฟล์ตาราง
- `test_conflict_detector.py`: ทดสอบ Hard Conflicts C1 ถึง C6 ครบทุกกรณี
- `test_quality_evaluator.py`: ทดสอบ Soft Rules W1 ถึง W5 ครบทุกเงื่อนไข
- `test_planner.py`: ทดสอบ CP-SAT Solver ในการจัดตาราง, Solution Diversity, และการเคารพ Preference วันว่าง
- `test_api.py`: ทดสอบ FastAPI Endpoints ทั้งหมด รวมถึง Path Alias ทุกเส้นทาง

### ตารางผลการรัน Pytest (27/27 ผ่านทั้งหมด 100%)

```
============================= test session starts ==============================
platform darwin -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
rootdir: ProJ-RMUTT-Planner/06_schedule_conflict_engine
collected 27 items

tests/test_api.py::test_health_check PASSED                              [  3%]
tests/test_api.py::test_conflicts_check_endpoint PASSED                  [  7%]
tests/test_api.py::test_validate_alias_endpoint PASSED                   [ 11%]
tests/test_api.py::test_preview_endpoint PASSED                          [ 14%]
tests/test_api.py::test_generate_plan_endpoint PASSED                    [ 18%]
tests/test_api.py::test_repair_endpoint PASSED                           [ 22%]
tests/test_api.py::test_compare_endpoint PASSED                          [ 25%]
tests/test_bitmask.py::test_bitmask_total_slots PASSED                   [ 29%]
tests/test_bitmask.py::test_touching_head_to_tail_no_clash PASSED        [ 33%]
tests/test_bitmask.py::test_overlapping_classes_clash PASSED             [ 37%]
tests/test_bitmask.py::test_different_days_no_clash PASSED               [ 40%]
tests/test_bitmask.py::test_spanning_noon PASSED                         [ 44%]
tests/test_bitmask.py::test_schedule_profile_analysis PASSED             [ 48%]
tests/test_conflict_detector.py::test_c1_time_clash PASSED               [ 51%]
tests/test_conflict_detector.py::test_c2_exam_clash PASSED               [ 55%]
tests/test_conflict_detector.py::test_c3_prereq_fail PASSED              [ 59%]
tests/test_conflict_detector.py::test_c4_credit_limit_exceeded PASSED    [ 62%]
tests/test_conflict_detector.py::test_c4_summer_credit_limit PASSED      [ 66%]
tests/test_conflict_detector.py::test_c5_duplicate_sections PASSED       [ 70%]
tests/test_conflict_detector.py::test_c6_seat_full PASSED                [ 74%]
tests/test_planner.py::test_cp_sat_generates_valid_plans PASSED          [ 77%]
tests/test_planner.py::test_cp_sat_respects_free_day_preference PASSED   [ 81%]
tests/test_quality_evaluator.py::test_w1_long_stretch PASSED             [ 85%]
tests/test_quality_evaluator.py::test_w2_large_gap PASSED                [ 88%]
tests/test_quality_evaluator.py::test_w3_early_morning_and_free_days PASSED [ 92%]
tests/test_quality_evaluator.py::test_w4_rush_building_move PASSED       [ 96%]
tests/test_quality_evaluator.py::test_w5_heavy_days PASSED               [100%]

======================== 27 passed in 1.29s =========================
```

### ผลการตรวจความปลอดภัยและกติกาโปรเจกต์ (CI Compliance)
- **Syntax Check**: `python -m compileall -q 0*/src` $\rightarrow$ ผ่าน 100% ไม่มีข้อผิดพลาด
- **Secrets & PDPA Guard**: ไม่มีไฟล์ `.env`, ไม่มี API Key, และไม่มีรหัสนักศึกษาจริงหลุดเข้าไปในโค้ด
- **Docker Compose**: คอนฟิกพอร์ต `:8600` และ Healthcheck สอดคล้องกับ `docker-compose.yml`
