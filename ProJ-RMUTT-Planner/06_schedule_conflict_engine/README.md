# โมดูล 06: ระบบตรวจสอบข้อขัดแย้งของตารางเรียนและการจัดตารางอัตโนมัติ
## (Schedule Conflict Engine & Automated Timetable Planner)

**เอกสารข้อกำหนดทางเทคนิคและสถาปัตยกรรมระบบ (Technical Specification & Architecture Documentation)**  
- **โครงการ:** ระบบวางแผนการเรียนและจัดตารางเรียนอัจฉริยะ (RMUTT Study Planner)  
- **ผู้รับผิดชอบระบบ:** นายชีวากร อาจดีลัง  
- **กิ่งพัฒนา (Git Branch):** `feat/schedule-enging`  

---

## 1. บทคัดย่อและขอบเขตของระบบ (Abstract & Scope)

โมดูล 06 ทำหน้าที่เป็น **แกนหลักเชิงตรรกะและคณิตศาสตร์ (Core Computational Engine)** ของระบบ RMUTT Study Planner มีหน้าที่หลัก 3 ประการ:
1. **การตรวจสอบข้อขัดแย้งของตารางเรียน (Schedule Conflict Detection):** ตรวจสอบความถูกต้องตามกฎระเบียบของมหาวิทยาลัยและข้อจำกัดทางกายภาพ 6 มิติ (Hard Constraints C1–C6)
2. **การประเมินคุณภาพชีวิตและสุขภาวะการเรียน (Quality-of-Life Evaluation):** ประเมินและแจ้งเตือนข้อจำกัดเชิงคุณภาพ 5 มิติ (Soft Constraints W1–W5)
3. **การแก้ปัญหาการจัดตารางเรียนแบบหาความพึงพอใจสูงสุด (Automated Schedule Optimization):** ประมวลผลและสร้างแผนการเรียนทางเลือกจำนวน 3–5 แผน ด้วยแบบจำลอง Constraint Programming (CP-SAT)

---

## 2. หลักการออกแบบทางวิศวกรรมซอฟต์แวร์ (Engineering Design Principles)

### 2.1 การแยกตรรกะเชิงกำหนดออกจากโมเดลภาษา (Separation of Deterministic Logic from Probabilistic Models)

ในการพัฒนาระบบร่วมกับ Large Language Models (LLMs) ทีมพัฒนาได้กำหนดข้อตกลงทางสถาปัตยกรรม (Architectural Decision):
> **"โมเดลภาษาต้องไม่มีบทบาทในการตัดสินเงื่อนไขเวลาหรือการคำนวณทางคณิตศาสตร์"**

- **ข้อจำกัดของโมเดลภาษา:** LLM มีสถาปัตยกรรมแบบทำนายความน่าจะเป็นของโทเคน (Probabilistic Token Prediction) ซึ่งมีอัตราความผิดพลาดด้านการคำนวณทางคณิตศาสตร์และตรรกศาสตร์เชิงเวลา (Temporal Reasoning Hallucination) สูงถึง 15–30% จากการทดสอบเบื้องต้น
- **ความสำคัญของความถูกต้องเชิงระบบ:** การคำนวณว่าวิชาเรียนทับซ้อนกันหรือไม่ เป็นปัญหาที่ต้องมีความถูกต้องสัมบูรณ์ (100% Deterministic Correctness)
- **แนวทางแก้ไข:** ออกแบบให้โมดูล 06 ทำหน้าที่ประมวลผลกฎทั้งหมดในลักษณะ Rule Engine และ Optimization Solver อย่างเป็นอิสระ แล้วส่งออกผลลัพธ์ในรูปแบบโครงสร้างข้อมูลมาตรฐาน (Structured Data/JSON) ให้โมดูล 07 นำไปสร้างคำอธิบายเป็นภาษาธรรมชาติ (Natural Language Explanation)

```text
[ผู้ใช้งาน / Frontend]
        │
        ▼ (HTTP Request)
[06_schedule_conflict_engine] ───(ประมวลผลเชิงกำหนด 100%)───┐
        │                                                    │
        ▼ (Structured Result / JSON)                         │
[07_rag_llm_engine]                                          ▼
        │ (สร้างภาษาธรรมชาติเพื่ออธิบาย)             [01_web_app / 02_api_backend]
        ▼                                           (แสดงผลตาราง / บันทึกฐานข้อมูล)
"วิชา CPE101 ชนกับ CPE102 ในวันจันทร์..."
```

---

## 3. ทฤษฎีและการออกแบบอัลกอริทึม (Theoretical Foundations & Algorithms)

### 3.1 การแทนช่วงเวลาด้วยระบบบิตมาร์ก 182 บิต (182-Bitmask Temporal Representation)

เพื่อรองรับการตรวจสอบการทับซ้อนของตารางเรียนแบบเรียลไทม์ที่มีความถี่สูง (เช่น ในกรณี Drag & Drop บนเว็บแอปพลิเคชัน) ระบบได้ออกแบบโครงสร้างข้อมูลแบบบิตมาร์กขนาด 182 บิต:

#### การคำนวณมิติของบิต (Dimension Mapping):
- **จำนวนวันใน 1 สัปดาห์:** 7 วัน (วันจันทร์ = Index 0 จนถึง วันอาทิตย์ = Index 6)
- **กรอบเวลาเรียนต่อวัน:** 08:00 น. ถึง 21:00 น. (รวม 13 ชั่วโมง หรือ 780 นาทีต่อวัน)
- **หน่วยย่อยของเวลา (Granularity):** ช่องละ 30 นาที $\rightarrow$ 26 สล็อตต่อวัน
- **ขนาดบิตทั้งหมด:**
  $$\text{Total Bits} = 7 \times 26 = 182 \text{ บิต}$$

#### ตำแหน่งบิต (Bit Indexing Function):
กำหนดให้ $d \in \{0, 1, \dots, 6\}$ แทนวัน และ $t_{\text{start}}, t_{\text{end}}$ แทนเวลาเริ่มต้นและสิ้นสุดในหน่วยนาทีจากเที่ยงคืน:
$$\text{Slot}_{\text{start}} = \left\lfloor \frac{\max(t_{\text{start}}, 480) - 480}{30} \right\rfloor$$
$$\text{Slot}_{\text{end}} = \min\left(26, \left\lceil \frac{\min(t_{\text{end}}, 1260) - 480}{30} \right\rceil\right)$$
$$\text{Bit Index} = (d \times 26) + \text{slot} \quad \text{สำหรับ } \text{slot} \in [\text{Slot}_{\text{start}}, \text{Slot}_{\text{end}})$$

#### ประสิทธิภาพเชิงเวลา (Computational Complexity):
- **การตรวจสอบเวลาชน (Collision Check):**
  $$\text{IsClash}(A, B) \iff (\text{Mask}_A \land \text{Mask}_B) \ne 0$$
  ดำเนินการด้วยการคำนวณระดับ Bitwise AND ระดับฮาร์ดแวร์ ใช้ความซับซ้อนเชิงเวลา $O(1)$
- **การถอดรหัสบิตชน (Bit Decoding):** ทำการสแกนเฉพาะบิตที่เปิดอยู่ในผลลัพธ์ $\text{Mask}_A \land \text{Mask}_B$ เพื่อแปลงกลับเป็นช่วงเวลาเริ่มต้นและสิ้นสุดอย่างแม่นยำ

---

### 3.2 การแก้ปัญหาการจัดตารางด้วย Google OR-Tools CP-SAT (Constraint Programming)

ปัญหาการจัดตารางเรียนจัดอยู่ในกลุ่มปัญหา **Combinatorial Optimization (NP-hard)** ซึ่งการใช้วิธีค้นหาแบบสุ่ม (Heuristic) ไม่สามารถรับประกันว่าจะได้คำตอบที่ดีที่สุด หรืออาจใช้เวลาคำนวณนานเกินขอบเขต ระบบจึงเลือกใช้ **Constraint Programming over Satisfiability (CP-SAT)**:

#### 1. ตัวแปรตัดสินใจ (Decision Variables):
สำหรับกลุ่มเรียน $s \in S$:
$$x_s \in \{0, 1\} \quad \text{โดยที่ } x_s = 1 \text{ หากเลือกกลุ่มเรียน } s$$
สำหรับวันที่มีการเรียน $d \in \{0, 1, \dots, 6\}$:
$$y_d \in \{0, 1\} \quad \text{โดยที่ } y_d = 1 \text{ หากมีวิชาเรียนในวัน } d$$

#### 2. ข้อจำกัดบังคับ (Hard Constraints):
1. **การเลือกกลุ่มเรียนต่อหนึ่งรายวิชา (At Most One Section):**
   $$\sum_{s \in S_c} x_s \le 1 \quad \forall c \in C$$
2. **การปราศจากเวลาเรียนและเวลาสอบทับซ้อน (Non-Overlapping):**
   $$x_u + x_v \le 1 \quad \forall (u, v) \in \text{ClashPairs}$$
3. **ขอบเขตหน่วยกิตรวม (Credit Boundaries):**
   $$\text{MinCredits} \le \sum_{s \in S} \text{Credits}(s) \cdot x_s \le \text{MaxCredits}$$
4. **ความสัมพันธ์ของวันที่มีเรียน (Day Usage Linkage):**
   $$y_d \ge x_s \quad \forall s \in S \text{ ที่มีคาบเรียนในวัน } d$$

#### 3. ฟังก์ชันวัตถุประสงค์ (Multi-Objective Maximization):
$$\max Z = \sum_{s \in S} \left( W_{\text{priority}} \cdot P_s \cdot x_s \right) - \sum_{d \in D_{\text{free}}} \left( W_{\text{free}} \cdot y_d \right) - \sum_{s \in S_{\text{morning}}} \left( W_{\text{morning}} \cdot x_s \right) - \sum_{d=0}^{6} \left( W_{\text{campus}} \cdot y_d \right)$$
- $P_s$: คะแนนความสำคัญของรายวิชาตาม Critical Path (P0=Retake, P1=ตามแผนเทอม, P2=ปลดล็อกวิชาอื่น, P3=วิชาเลือก)
- $D_{\text{free}}$: ชุดวันที่นักศึกษาต้องการให้เป็นวันว่าง
- $S_{\text{morning}}$: ชุดกลุ่มเรียนที่มีคาบเรียนช่วงเช้า (ก่อน 09:00 น.)

#### 4. การสร้างชุดคำตอบที่หลากหลาย (Solution Pool Diversity):
เมื่อได้คำตอบแผนที่ $k$ ระบบจะเพิ่มข้อจำกัดตัดคำตอบเดิม (Cut Constraint):
$$\sum_{s \in \text{Plan}_k} x_s \le |\text{Plan}_k| - 1$$
แล้วดำเนินการแก้ปัญหาใหม่ซ้ำเพื่อสร้างแผนทางเลือกที่ 2 ถึง 5 ตามลำดับ

#### 5. ลำดับขั้นการผ่อนปรนข้อจำกัด (Hierarchical Constraint Relaxation):
หากโมเดลไม่สามารถหาผลลัพธ์ที่เป็นไปได้ (Infeasible) ระบบจะดำเนินการผ่อนปรนข้อจำกัดตามลำดับ:
- **ระดับที่ 1 (Relax Preferences):** ยกเลิกเงื่อนไขการหลีกเลี่ยงคาบเช้าและวันว่าง
- **ระดับที่ 2 (Relax Capacity):** อนุญาตให้เลือกกลุ่มเรียนที่ที่นั่งเต็ม พร้อมระบุคำแนะนำขอโควตา
- **ระดับที่ 3 (Relax Credits):** ปรับลดเกณฑ์หน่วยกิตขั้นต่ำ เพื่อให้ระบบสามารถจัดวิชาที่จำเป็นที่สุดให้ได้

---

## 4. ข้อกำหนดกฎการตรวจสอบ (Constraint Classification)

### 4.1 ข้อจำกัดแบบเคร่งครัด (Hard Constraints: C1 – C6)
ฝ่าฝืนกฎเหล่านี้จะส่งผลให้ไม่สามารถลงทะเบียนเรียนได้จริง

| รหัส | ชื่อกฎ | คำอธิบายเงื่อนไข | ระดับความรุนแรง |
|---|---|---|---|
| **C1** | `TIME_CLASH` | คาบเรียนมีช่วงเวลาทับซ้อนกันตั้งแต่ 30 นาทีขึ้นไป | `ERROR` |
| **C2** | `EXAM_CLASH` | วันและช่วงเวลาสอบกลางภาคหรือสอบปลายภาคตรงกัน | `ERROR` |
| **C3** | `PREREQ_FAIL` | นักศึกษายังไม่ผ่านรายวิชาบังคับก่อนตามโครงสร้างหลักสูตร | `ERROR` |
| **C4** | `CREDIT_LIMIT` | หน่วยกิตรวมเกิน 21 หน่วยกิต (ภาคปกติ) / เกิน 9 หน่วยกิต (ภาคฤดูร้อน) หรือต่ำกว่า 9 หน่วยกิต | `ERROR` / `WARNING` |
| **C5** | `DUPLICATE` | เลือกลงทะเบียนซ้ำมากกว่า 1 กลุ่มในวิชาเดียวกัน หรือลงวิชาที่เคยสอบผ่านแล้ว | `ERROR` |
| **C6** | `SEAT_FULL` | จำนวนผู้ลงทะเบียนในกลุ่มเรียนเต็มจำนวนรับที่ระบุ | `ERROR` |

### 4.2 ข้อจำกัดเชิงคุณภาพและสุขภาวะการเรียน (Soft Constraints: W1 – W5)
ส่งผลกระทบต่อคุณภาพชีวิตและประสิทธิภาพในการเรียนของนักศึกษา

| รหัส | ชื่อกฎ | คำอธิบายเงื่อนไข | ระดับความรุนแรง |
|---|---|---|---|
| **W1** | `LONG_STRETCH` | มีการเรียนติดต่อกันยาวนานเกิน 6 ชั่วโมงโดยไม่มีช่วงเวลาพัก | `WARNING` |
| **W2** | `LARGE_GAP` | มีช่วงเวลารอเรียนระหว่างคาบในวันเดียวกันยาวนานเกิน 4 ชั่วโมง | `WARNING` |
| **W3** | `EARLY_CLASS` | มีคาบเรียนเวลา 08:00 น. หรือมีคาบเรียนในวันที่ระบุความต้องการเป็นวันว่าง | `WARNING` |
| **W4** | `RUSH_MOVE` | ต้องเปลี่ยนอาคารเรียนหรือวิทยาเขตระหว่างคาบที่มีเวลาพักน้อยกว่า 15 นาที | `WARNING` |
| **W5** | `HEAVY_DAYS` | ตารางเรียนกระจายตัวจนต้องเดินทางมามหาวิทยาลัย 6 ถึง 7 วันต่อสัปดาห์ | `WARNING` |

---

## 5. ข้อกำหนดส่วนต่อประสานโปรแกรมประยุกต์ (API Specification)

ระบบพัฒนาบนพื้นฐานของ FastAPI รองรับการสื่อสารผ่านโพรโทคอล HTTP/JSON:

| เมธอด | เส้นทาง (Endpoint) | หน้าที่การทำงาน | ความเข้ากันได้ของระบบ |
|---|---|---|---|
| `GET` | `/health` | ตรวจสอบสถานะความพร้อมของบริการ (Health Check) | Docker, CI Runner |
| `POST` | `/conflicts/check` | ตรวจสอบข้อขัดแย้ง C1–C6 และ W1–W5 แบบละเอียด | โมดูล 03 (`ai_router_agent`) |
| `POST` | `/validate` | ส่วนต่อประสานเสมือนสำหรับตรวจสอบความถูกต้องของแผน | โมดูล 02 (`api_backend`) |
| `POST` | `/conflicts/preview` | ตรวจสอบเฉพาะเวลาชนด้วย Bitmask ความเร็วสูง (< 50ms) | โมดูล 01 (`web_app` Drag & Drop) |
| `POST` | `/plan/generate` | จัดแผนการเรียนอัตโนมัติ 3–5 แผนด้วย CP-SAT Solver | สเปกกลางโมดูล 06 |
| `POST` | `/plans/auto` | ส่วนต่อประสานเสมือนสำหรับการสร้างแผนอัตโนมัติ | โมดูล 03 (`ai_router_agent`) |
| `POST` | `/generate` | ส่วนต่อประสานเสมือนสำหรับการสร้างแผนอัตโนมัติ | โมดูล 02 (`api_backend`) |
| `POST` | `/plan/repair` | วิเคราะห์ตารางที่ชนและเสนอแนะกลุ่มเรียนทางเลือกที่ไม่ชน | โมดูล 01, 02 |
| `POST` | `/plan/compare` | เปรียบเทียบความแตกต่างระหว่างแผนการเรียน 2 แผน | โมดูล 01, 08 |

---

## 6. รายงานผลการทดสอบระบบ (Verification & Test Report)

การทดสอบระบบดำเนินการครอบคลุมระดับ Unit Test และ Integration Test รวมทั้งสิ้น 27 กรณีทดสอบ ด้วยเฟรมเวิร์ก Pytest:

```text
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

### สรุปผลการตรวจสอบด้านความถูกต้องและความปลอดภัย:
1. **ความถูกต้องของตรรกะ (Logical Verification):** การทดสอบครอบคลุมกรณีขอบเขตเวลา (Edge Cases) เช่น คาบเรียนที่ติดกันพอดีหัวท้าย (11:00 น. กับ 11:00 น.) ตรวจสอบแล้วว่าไม่เกิดการชนกันอย่างถูกต้อง
2. **การปฏิบัติตามมาตรฐานความปลอดภัย (Security & Secrets Guard):** ผ่านเกณฑ์การตรวจสอบของ CI โดยไม่มีการจัดเก็บข้อมูลส่วนบุคคลของนักศึกษาจริง ไม่มีคีย์รหัสผ่านหรือ API Key และไม่มีไฟล์ `.env` อยู่ในระบบการควบคุมเวอร์ชัน
3. **การตรวจสอบไวยากรณ์ (Syntax Compilation):** ตรวจสอบผ่านคำสั่ง `python -m compileall -q 0*/src` สำเร็จสมบูรณ์ 100%
