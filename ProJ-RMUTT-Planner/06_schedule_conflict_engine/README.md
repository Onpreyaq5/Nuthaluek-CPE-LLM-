# โมดูล 06: ระบบตรวจสอบข้อขัดแย้งของตารางเรียนและการจัดตารางอัตโนมัติ
## (Schedule Conflict Engine & Automated Timetable Planner)

**เอกสารข้อกำหนดทางเทคนิคและสถาปัตยกรรมระบบ (Technical Specification & Architecture Documentation)**  
- **โครงการ:** ระบบวางแผนการเรียนและจัดตารางเรียนอัจฉริยะ (RMUTT Study Planner)  
- **ผู้รับผิดชอบระบบ:** นายชีวากร อาจดีลัง  
- **กิ่งพัฒนา (Git Branch):** `feat/schedule-enging`  

---

## 1. บทคัดย่อและขอบเขตของระบบ (Abstract & Scope)

โมดูล 06 ทำหน้าที่เป็น **แกนหลักเชิงตรรกะและคณิตศาสตร์ (Core Computational Engine)** ของระบบ RMUTT Study Planner มีขอบเขตการทำงานหลัก 3 ประการ:
1. **การตรวจสอบข้อขัดแย้งของตารางเรียน (Schedule Conflict Detection):** ตรวจสอบความถูกต้องตามกฎระเบียบของมหาวิทยาลัยและข้อจำกัดทางกายภาพ 6 มิติ (Hard Constraints C1–C6)
2. **การประเมินคุณภาพชีวิตและสุขภาวะการเรียน (Quality-of-Life Evaluation):** ประเมินและแจ้งเตือนข้อจำกัดเชิงคุณภาพ 5 มิติ (Soft Constraints W1–W5)
3. **การแก้ปัญหาการจัดตารางเรียนแบบหาความพึงพอใจสูงสุด (Automated Schedule Optimization):** ประมวลผลและสร้างแผนการเรียนทางเลือกจำนวน 3–5 แผน ด้วยแบบจำลอง Constraint Programming (CP-SAT)

ระบบได้รับการออกแบบให้ทำงานร่วมกับโมดูลภายนอกอย่างสมบูรณ์ โดยรองรับสัญญาการทำงาน (Contracts) ของ **โมดูล 02 (`02_api_backend`)** และ **โมดูล 03 (`03_ai_router_agent`)** รวมถึงเชื่อมต่อข้อมูลผ่าน Data Provider ไปยัง **โมดูล 04 (`04_data_integration`)** และ **โมดูล 05 (`05_student_profile`)**

---

## 2. หลักการออกแบบทางวิศวกรรมซอฟต์แวร์ (Engineering Design Principles)

### 2.1 การแยกตรรกะเชิงกำหนดออกจากโมเดลภาษา (Separation of Deterministic Logic from Probabilistic Models)

ในการพัฒนาระบบร่วมกับ Large Language Models (LLMs) สถาปัตยกรรมระบบถูกออกแบบตามหลักการสำคัญ:
> **"โมเดลภาษาต้องไม่มีบทบาทในการตัดสินเงื่อนไขเวลาหรือการคำนวณทางคณิตศาสตร์"**

- **ข้อจำกัดของโมเดลภาษา:** โมเดลภาษาทำงานด้วยสถาปัตยกรรมทำนายความน่าจะเป็นของโทเคน (Probabilistic Token Prediction) ซึ่งมีความเสี่ยงต่อความผิดพลาดเชิงตรรกะเวลาและการคำนวณ (Temporal Hallucination)
- **ความถูกต้องสัมบูรณ์ (100% Deterministic Correctness):** การพิจารณาว่าวิชาเรียนทับซ้อนกันหรือไม่ หรือหน่วยกิตอยู่ในกรอบกฎระเบียบหรือไม่ เป็นปัญหาเชิงตรรกะที่ยอมรับความผิดพลาดไม่ได้
- **แนวทางสถาปัตยกรรม:** โมดูล 06 ทำหน้าที่เป็น Rule Engine และ Constraint Solver อย่างอิสระ คืนผลลัพธ์เป็นข้อมูลโครงสร้างมาตรฐาน (Structured JSON) โดยโมดูล 07 มีหน้าที่เพียงนำข้อมูลนี้ไปแปลงเป็นภาษาธรรมชาติเท่านั้น

### 2.2 แผนผังการทำงานและการเชื่อมต่อระหว่างโมดูล (System Architecture Diagram)

```text
       ┌────────────────────────┐         ┌─────────────────────────┐
       │   02_api_backend       │         │   03_ai_router_agent    │
       │   (Direct Endpoints)   │         │   (Routing & Dispatch)  │
       └───────────┬────────────┘         └────────────┬────────────┘
                   │                                   │
      POST /validate, /generate            POST /conflicts/check, /plans/auto
                   │                                   │
                   ▼                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   06_schedule_conflict_engine                          │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                        API Routing Layer                       │   │
│   │   - schemas_backend.py (02)       - schemas_router.py (03)     │   │
│   └───────────────┬────────────────────────────────┬───────────────┘   │
│                   │                                │                   │
│   ┌───────────────▼───────────────┐┌───────────────▼───────────────┐   │
│   │      Validation Service       ││       Planning Service        │   │
│   │  (Conflict & Quality Checking)││     (OR-Tools CP-SAT Solver)  │   │
│   └───────────────┬───────────────┘└───────────────┬───────────────┘   │
│                   │                                │                   │
│   ┌───────────────▼────────────────────────────────▼───────────────┐   │
│   │                 Core Conflict & Solver Engine                  │   │
│   │  - 182-Bitmask Time Clash      - Soft Constraint Evaluator     │   │
│   │  - Hard Constraints (C1 - C6)  - Solution Pool Generation      │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │                                    │
│   ┌───────────────────────────────▼────────────────────────────────┐   │
│   │                Provider Layer (Data Abstraction)               │   │
│   │      SectionProvider       │      StudentContextProvider       │   │
│   └───────────────┬────────────┴───────────────────┬───────────────┘   │
└───────────────────┼────────────────────────────────┼───────────────────┘
                    │ (HTTP / JSON)                  │ (HTTP / JSON)
                    ▼                                ▼
       ┌────────────────────────┐         ┌─────────────────────────┐
       │  04_data_integration   │         │   05_student_profile    │
       │  (Course & Section DB) │         │  (Student Anonymized)   │
       └────────────────────────┘         └─────────────────────────┘
```

---

## 3. ทฤษฎีและการออกแบบอัลกอริทึม (Theoretical Foundations & Algorithms)

### 3.1 การแทนช่วงเวลาด้วยระบบบิตมาร์ก 182 บิต (182-Bitmask Temporal Representation)

เพื่อรองรับการคำนวณการทับซ้อนของตารางเรียนแบบความเร็วสูงพิเศษ ระบบได้ออกแบบโครงสร้างข้อมูลบิตมาร์กขนาด 182 บิต:

#### การคำนวณมิติของบิต (Dimension Mapping):
- **จำนวนวันใน 1 สัปดาห์:** 7 วัน (จันทร์ = Index 0 ถึง อาทิตย์ = Index 6)
- **กรอบเวลาเรียนต่อวัน:** 08:00 น. ถึง 21:00 น. (13 ชั่วโมง หรือ 780 นาทีต่อวัน)
- **หน่วยย่อยของเวลา (Granularity):** ช่วงละ 30 นาที $\rightarrow$ 26 สล็อตต่อวัน
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
  คำนวณด้วย Bitwise AND ระดับฮาร์ดแวร์ ใช้ความซับซ้อนเชิงเวลา $O(1)$
- **การถอดรหัสบิตชน (Bit Decoding):** ทำการประมวลผลเฉพาะบิตที่เปิดอยู่ในผลลัพธ์ $\text{Mask}_A \land \text{Mask}_B$ เพื่อแปลงกลับเป็นช่วงเวลาเริ่มต้นและสิ้นสุดอย่างแม่นยำ

### 3.2 การแก้ปัญหาการจัดตารางด้วย Google OR-Tools CP-SAT

การจัดตารางเรียนเป็นปัญหาประเภท Combinatorial Optimization (NP-hard) ระบบใช้แบบจำลองทางคณิตศาสตร์ด้วย Constraint Programming over Satisfiability (CP-SAT):

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
- $P_s$: ลำดับความสำคัญของรายวิชา (P0=Retake, P1=ตามแผนเทอม, P2=ปลดล็อกวิชาอื่น, P3=วิชาเลือก)
- $D_{\text{free}}$: ชุดวันที่ผู้ใช้ต้องการให้เป็นวันว่าง
- $S_{\text{morning}}$: กลุ่มเรียนช่วงเช้า (ก่อน 09:00 น.)

#### 4. การสร้างชุดคำตอบที่หลากหลาย (Solution Pool Diversity):
เมื่อได้คำตอบแผนที่ $k$ ระบบจะเพิ่มข้อจำกัดตัดคำตอบเดิม (Cut Constraint):
$$\sum_{s \in \text{Plan}_k} x_s \le |\text{Plan}_k| - 1$$
และดำเนินการแก้ปัญหาใหม่เพื่อสร้างแผนทางเลือกที่ 2 ถึง 5 ตามลำดับ

#### 5. ลำดับขั้นการผ่อนปรนข้อจำกัด (Hierarchical Constraint Relaxation):
หากไม่สามารถหาผลลัพธ์ที่เป็นไปได้ (Infeasible) ระบบจะผ่อนปรนข้อจำกัดตามลำดับ:
- ระดับที่ 1: ผ่อนปรนความพึงพอใจ (คาบเช้าและวันว่าง)
- ระดับที่ 2: ผ่อนปรนโควตาที่นั่ง พร้อมออกคำแนะนำขอโควตา
- ระดับที่ 3: ผ่อนปรนหน่วยกิตขั้นต่ำ เพื่อให้สามารถลงทะเบียนวิชาที่จำเป็นที่สุดได้

---

## 4. ข้อกำหนดกฎการตรวจสอบ (Constraint Classification)

### 4.1 ข้อจำกัดแบบเคร่งครัด (Hard Constraints: C1 – C6)
| รหัส | ชื่อกฎ | คำอธิบายเงื่อนไข | ระดับความรุนแรง |
|---|---|---|---|
| **C1** | `TIME_CLASH` | คาบเรียนมีช่วงเวลาทับซ้อนกันตั้งแต่ 30 นาทีขึ้นไป | `ERROR` |
| **C2** | `EXAM_CLASH` | วันและช่วงเวลาสอบกลางภาคหรือสอบปลายภาคตรงกัน | `ERROR` |
| **C3** | `PREREQ_FAIL` | นักศึกษายังไม่ผ่านรายวิชาบังคับก่อนตามโครงสร้างหลักสูตร | `ERROR` |
| **C4** | `CREDIT_LIMIT` | หน่วยกิตรวมเกิน 21 หน่วยกิต (ภาคปกติ) / เกิน 9 หน่วยกิต (ภาคฤดูร้อน) หรือต่ำกว่า 9 หน่วยกิต | `ERROR` / `WARNING` |
| **C5** | `DUPLICATE` | เลือกลงทะเบียนซ้ำมากกว่า 1 กลุ่มในวิชาเดียวกัน หรือลงวิชาที่เคยสอบผ่านแล้ว | `ERROR` |
| **C6** | `SEAT_FULL` | จำนวนผู้ลงทะเบียนในกลุ่มเรียนเต็มจำนวนรับที่ระบุ | `ERROR` |

### 4.2 ข้อจำกัดเชิงคุณภาพและสุขภาวะการเรียน (Soft Constraints: W1 – W5)
| รหัส | ชื่อกฎ | คำอธิบายเงื่อนไข | ระดับความรุนแรง |
|---|---|---|---|
| **W1** | `LONG_STRETCH` | มีการเรียนติดต่อกันยาวนานเกิน 6 ชั่วโมงโดยไม่มีช่วงเวลาพัก | `WARNING` |
| **W2** | `LARGE_GAP` | มีช่วงเวลารอเรียนระหว่างคาบในวันเดียวกันยาวนานเกิน 4 ชั่วโมง | `WARNING` |
| **W3** | `EARLY_CLASS` | มีคาบเรียนเวลา 08:00 น. หรือมีคาบเรียนในวันที่ระบุความต้องการเป็นวันว่าง | `WARNING` |
| **W4** | `RUSH_MOVE` | ต้องเปลี่ยนอาคารเรียนหรือวิทยาเขตระหว่างคาบที่มีเวลาพักน้อยกว่า 15 นาที | `WARNING` |
| **W5** | `HEAVY_DAYS` | ตารางเรียนกระจายตัวจนต้องเดินทางมามหาวิทยาลัย 6 ถึง 7 วันต่อสัปดาห์ | `WARNING` |

---

## 5. รายละเอียดส่วนต่อประสานโปรแกรมประยุกต์และสัญญาข้อมูล (API Contracts)

โมดูล 06 รองรับการเรียกใช้งานผ่าน 4 Endpoints หลักที่สอดคล้องกับโมดูลต้นทาง 100%:

### 5.1 สัญญาของโมดูล 02 (`02_api_backend`)

#### 1. `POST /validate`
- **หน้าที่:** ตรวจสอบข้อขัดแย้งของกลุ่มเรียนที่ส่งเข้ามา
- **Request Body:**
  ```json
  {
    "term": "1/2567",
    "section_ids": ["01076001-1", "01076002-1"]
  }
  ```
- **Response Body (`BackendValidateResponse`):**
  ```json
  {
    "valid": false,
    "conflicts": [
      {
        "type": "TIME_CLASH",
        "message": "เวลาเรียนซ้อนทับกัน",
        "section_ids": ["01076001-1", "01076002-1"],
        "details": {
          "day": "MON",
          "overlap_start": "09:00",
          "overlap_end": "12:00"
        }
      }
    ]
  }
  ```

#### 2. `POST /generate`
- **หน้าที่:** สร้างแผนการเรียนแนะนำสำหรับนักศึกษา
- **Request Body:**
  ```json
  {
    "student_id": "STUDENT_HASH_001",
    "term": "1/2567",
    "max_credits": 21,
    "preferred_days": ["MON", "TUE", "WED", "THU"]
  }
  ```
- **Response Body (`BackendGenerateResponse`):**
  ```json
  {
    "plans": [
      {
        "sections": ["01076001-1", "01076002-1"],
        "warnings": [],
        "explanation": null
      }
    ]
  }
  ```

---

### 5.2 สัญญาของโมดูล 03 (`03_ai_router_agent`)

#### 3. `POST /conflicts/check`
- **หน้าที่:** ตรวจสอบข้อขัดแย้งเชิงเวลาและกฎเกณฑ์ พร้อมสรุปข้อมูลตารางเรียน
- **Request Body:**
  ```json
  {
    "sections": ["01076001-1", "01076002-1"]
  }
  ```
- **Response Body (`RouterConflictResponse`):**
  ```json
  {
    "has_conflict": true,
    "conflicts": [
      {
        "rule_code": "C1",
        "rule_name": "TIME_CLASH",
        "severity": "ERROR",
        "sections": ["01076001-1", "01076002-1"],
        "details": {
          "day": "MON",
          "overlap_start": "09:00",
          "overlap_end": "12:00"
        }
      }
    ],
    "warnings": [],
    "summary": {
      "total_credits": 6,
      "days_on_campus": 1,
      "free_days": ["TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    }
  }
  ```

#### 4. `POST /plans/auto`
- **หน้าที่:** สร้างแผนตารางเรียนอัตโนมัติตามความต้องการของ AI Router
- **Request Body:**
  ```json
  {
    "student_id": "STUDENT_HASH_001",
    "term": "1/2567",
    "preferences": {
      "avoid_morning": true,
      "free_days": ["FRI"]
    }
  }
  ```
- **Response Body (`RouterGenerateResponse`):**
  ```json
  {
    "plans": [
      {
        "plan_id": "plan_1",
        "sections": ["01076001-1", "01076002-1"],
        "total_credits": 6,
        "score": 85.5,
        "warnings": []
      }
    ],
    "total_candidates": 1,
    "solver_status": "OPTIMAL"
  }
  ```

---

### 5.3 ส่วนต่อประสานเฉพาะโมดูล 06 และระบบตรวจสอบสถานะ

| เมธอด | เส้นทาง (Endpoint) | หน้าที่การทำงาน | กลุ่มเป้าหมาย |
|---|---|---|---|
| `GET` | `/health` | ตรวจสอบสถานะการเปิดทำงานของแอปพลิเคชัน (Liveness Probe) | Docker, Kubernetes |
| `GET` | `/ready` | ตรวจสอบความพร้อมของหน่วยความจำและตัวแก้ปัญหา (Readiness Probe) | Ingress, CI Runner |
| `POST` | `/conflicts/preview` | ตรวจสอบเวลาชนแบบเร็วพิเศษ (< 50ms) | UI Drag & Drop (01) |
| `POST` | `/plan/generate` | จัดแผนการเรียนอัตโนมัติ 3–5 แผนพร้อมรายละเอียดสมบูรณ์ | โมดูล 06 สเปกเต็ม |
| `POST` | `/plan/repair` | วิเคราะห์ตารางที่ชนและเสนอแนะกลุ่มเรียนทางเลือกที่ไม่ชน | โมดูล 01, 02 |
| `POST` | `/plan/compare` | เปรียบเทียบความแตกต่างและคุณภาพระหว่าง 2 แผน | โมดูล 01, 08 |

---

## 6. สถาปัตยกรรมการแปลงข้อมูลและการเชื่อมต่อบริการภายนอก (Data Providers)

### 6.1 กลไกการ Resolve ข้อมูล Section และ Student Context

โมดูล 06 ใช้แนวคิด **Protocol-based Dependency Injection** ในการตัดขาดการยึดติดกับแหล่งข้อมูล:
1. **`SectionProvider` Protocol:**
   - กำหนดเมธอด `get_sections(section_ids: list[str]) -> list[Section]` และ `get_available_sections(term: str) -> list[Section]`
   - `HttpSectionProvider`: ติดต่อไปยัง โมดูล 04 ผ่าน HTTP เพื่อดึงข้อมูลจริง
   - `MemorySectionProvider`: ใช้สำหรับกระบวนการทดสอบ Unit Test และโหมดการทำงานจำลอง
2. **`StudentContextProvider` Protocol:**
   - กำหนดเมธอด `get_student_context(student_id: str) -> StudentProfile`
   - `HttpStudentContextProvider`: ติดต่อไปยัง โมดูล 05 (`GET /context/{student_id}`) เพื่อดึงประวัติการเรียนและข้อมูลหลักสูตร
   - ข้อมูล `student_id` เป็น Synthetic Hash ตามมาตรฐานของระบบ

### 6.2 นโยบาย Fail-Closed และการจัดการข้อมูลไม่สมบูรณ์

- **ความสมบูรณ์ของข้อมูลคาบเรียน (Schedule Completeness):** หากกลุ่มเรียนที่ไม่ใช่วิชาประเภทออนไลน์ (`is_online == False`) ไม่มีข้อมูลคาบเรียนระบุไว้ (`meetings == []`) ระบบจะยกเว้นการประมวลผลและส่งข้อยกเว้น `DataIncompleteError` ทันที และตอบกลับเป็น HTTP 422
- **การไม่พบข้อมูล (Data Not Found):** หากไม่พบรหัสกลุ่มเรียนหรือรหัสนักศึกษาในฐานข้อมูลของโมดูล 04 หรือ 05 ระบบจะตอบกลับเป็น HTTP 422
- **ความขัดข้องของบริการต้นทาง (Upstream Failure):** หากบริการ 04 หรือ 05 มีปัญหาหรือเกิด Timeout ระบบจะตอบกลับเป็น HTTP 502 Bad Gateway

### 6.3 พฤติกรรม Mock / Demo และการแยกสภาพแวดล้อม

- ตัวแปรสภาพแวดล้อม `DEMO_MODE=false` ถูกตั้งค่าเป็นค่าเริ่มต้น (Default)
- ชุดข้อมูลจำลอง (Mock Fixtures) ถูกแยกไว้ใน `src/core/demo_fixtures.py` และจะถูกเรียกใช้เฉพาะเมื่อระบุ `DEMO_MODE=true` หรือในสภาพแวดล้อมการทดสอบเท่านั้น
- **ข้อกำหนดความปลอดภัย:** ห้ามใช้ Mock Data เป็น Fallback เงียบในสภาวะ Production โดยเด็ดขาด หากการเชื่อมต่อ upstream ขัดข้อง ระบบต้อง Fail-Closed ทันที

---

## 7. รายงานผลการทดสอบระบบ (Verification & Test Report)

ชุดการทดสอบครอบคลุมทั้ง Unit Test, Contract Testing ของโมดูล 02 และ 03, และ Provider Testing รวมทั้งสิ้น 38 กรณีทดสอบ โดยผ่านการทดสอบสมบูรณ์ 100%:

```text
============================= test session starts ==============================
platform darwin -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
rootdir: ProJ-RMUTT-Planner/06_schedule_conflict_engine
collected 38 items

tests/test_api.py::test_health_check PASSED                              [  2%]
tests/test_api.py::test_ready_check PASSED                               [  5%]
tests/test_api.py::test_preview_endpoint PASSED                          [  7%]
tests/test_api.py::test_repair_endpoint PASSED                           [ 10%]
tests/test_api.py::test_compare_endpoint PASSED                          [ 13%]
tests/test_bitmask.py::test_bitmask_total_slots PASSED                   [ 15%]
tests/test_bitmask.py::test_touching_head_to_tail_no_clash PASSED        [ 18%]
tests/test_bitmask.py::test_overlapping_classes_clash PASSED             [ 21%]
tests/test_bitmask.py::test_different_days_no_clash PASSED               [ 23%]
tests/test_bitmask.py::test_spanning_noon PASSED                         [ 26%]
tests/test_bitmask.py::test_schedule_profile_analysis PASSED             [ 28%]
tests/test_conflict_detector.py::test_c1_time_clash PASSED               [ 31%]
tests/test_conflict_detector.py::test_c2_exam_clash PASSED               [ 34%]
tests/test_conflict_detector.py::test_c3_prereq_fail PASSED              [ 36%]
tests/test_conflict_detector.py::test_c4_credit_limit_exceeded PASSED    [ 39%]
tests/test_conflict_detector.py::test_c4_summer_credit_limit PASSED      [ 42%]
tests/test_conflict_detector.py::test_c5_duplicate_sections PASSED       [ 44%]
tests/test_conflict_detector.py::test_c6_seat_full PASSED                [ 47%]
tests/test_contract_backend.py::test_02_validate_conflict PASSED          [ 50%]
tests/test_contract_backend.py::test_02_validate_no_conflict PASSED       [ 52%]
tests/test_contract_backend.py::test_02_generate_plan PASSED              [ 55%]
tests/test_contract_router.py::test_03_check_conflicts_format PASSED      [ 57%]
tests/test_contract_router.py::test_03_check_conflicts_unknown_section_fails PASSED [ 60%]
tests/test_contract_router.py::test_03_auto_plan_format PASSED           [ 63%]
tests/test_contract_router.py::test_03_auto_plan_unknown_hash_fails PASSED [ 65%]
tests/test_planner.py::test_cp_sat_generates_valid_plans PASSED          [ 68%]
tests/test_planner.py::test_cp_sat_respects_free_day_preference PASSED   [ 71%]
tests/test_providers.py::test_memory_section_provider_found PASSED       [ 73%]
tests/test_providers.py::test_memory_section_provider_missing PASSED     [ 76%]
tests/test_providers.py::test_incomplete_section_data_fails PASSED      [ 78%]
tests/test_providers.py::test_memory_student_provider_found PASSED      [ 81%]
tests/test_providers.py::test_memory_student_provider_missing PASSED    [ 84%]
tests/test_providers.py::test_http_provider_network_error_raises_upstream_error PASSED [ 86%]
tests/test_quality_evaluator.py::test_w1_long_stretch PASSED             [ 89%]
tests/test_quality_evaluator.py::test_w2_large_gap PASSED                [ 92%]
tests/test_quality_evaluator.py::test_w3_early_morning_and_free_days PASSED [ 94%]
tests/test_quality_evaluator.py::test_w4_rush_building_move PASSED       [ 97%]
tests/test_quality_evaluator.py::test_w5_heavy_days PASSED               [100%]

======================== 38 passed in 1.44s ========================
```

---

## 8. รายการประสานงานและข้อกำหนดส่งมอบ (Handoff Specifications)

### 8.1 สำหรับโมดูล 04 (`04_data_integration`)
เพื่อให้ `HttpSectionProvider` ทำงานได้อย่างสมบูรณ์เมื่อเชื่อมต่อจริง:
1. **Endpoint ที่จำเป็น:**
   - แนะนำ: `POST /sections/batch` พร้อม Request Body `{"section_ids": ["..."]}` เพื่อดึงข้อมูลรายวิชาแบบชุด
   - หรือ `GET /sections?term={term}&ids={id1},{id2}`
2. **Schema ที่ส่งกลับ:** ต้องประกอบด้วย `section_id`, `course_code`, `course_name_th`, `course_name_en`, `credits`, `is_online`, `capacity`, `enrolled`, `meetings` (รายการวัน เวลาเริ่ม-จบในรูปนาทีจากเที่ยงคืน) และ `exam` (วัน เวลาสอบกลางภาค/ปลายภาค)

### 8.2 สำหรับโมดูล 05 (`05_student_profile`)
เพื่อให้ `HttpStudentContextProvider` ทำงานได้อย่างสมบูรณ์:
1. **Endpoint ที่ใช้งาน:**
   - `GET /context/{student_id}` (โดย `student_id` เป็น synthetic hash)
2. **Schema ที่ส่งกลับ:** ต้องประกอบด้วย `student_id`, `completed_courses`, `enrolled_courses`, `curriculum_plan` (แผนการเรียนตามเทอมเพื่อจัดลำดับ P0–P3) และ `max_credits`
