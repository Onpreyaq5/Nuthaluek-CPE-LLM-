# 05_data_integration — Data Integration & Student Context Service

โมดูลทำความสะอาดและแปลงข้อมูลรายวิชา/ตารางสอน (Course & Schedule Data Normalization), ตรวจสอบวิชาบังคับก่อนด้วย Directed Acyclic Graph (Prereq DAG), และจัดเตรียม Context ของนักศึกษา (Student Context) ส่งต่อให้โมดูล AI Router (03), Schedule Conflict Engine (06), และ RAG LLM Engine (07)

---

## สถาปัตยกรรมและการทำงาน (Key Features)

1. **Time Slot Bitmask Model (182-bit)**:
   - แปลงวันและเวลาเรียน (08:00–21:00, ช่องละ 30 นาที, 7 วัน = 182 บิต) เป็นตัวเลขบิต
   - ตรวจสอบเวลาชนแบบ $O(1)$ ด้วย `(mask_a & mask_b) != 0`
   - มีฟังก์ชันถอดรหัสบิตที่ซ้อนทับกลับเป็นช่วงเวลาจริง เช่น `MON 09:00 - 10:30`
2. **Course Normalizer & Fuzzy Search**:
   - ทำความสะอาดรหัสวิชา ตัดช่องว่าง ปรับตัวพิมพ์ใหญ่
   - แยกโครงสร้างหน่วยกิต `3(2-2-5)` เป็น credits=3, lecture=2, lab=2, self_study=5
   - ค้นหารายวิชาแม้สะกดผิดด้วย `RapidFuzz`
3. **Prerequisite DAG & Critical Path Engine**:
   - ใช้ `NetworkX` สร้าง DAG ของวิชาบังคับก่อน
   - ตรวจจับ Cycle (ความผิดพลาดในโครงสร้างหลักสูตร)
   - คำนวณวิชาที่ปลดล็อกแล้ว (Eligible Courses) ตามประวัติการเรียน
   - คำนวณคะแนน Critical Path เพื่อจัดลำดับความสำคัญวิชาที่เป็นตัวต่อหลัก (P2_UNLOCK)
4. **Student Context Aggregator**:
   - รวม Profile + Transcript + Degree Audit + ความชอบ (Preferences)
   - คำนวณ GPAX, หน่วยกิตสะสม, หน่วยกิตคงเหลือแยกตามหมวดหมู่, และปีที่คาดว่าจะสำเร็จการศึกษา
5. **Transcript Parser**:
   - รองรับการอ่านผลการเรียนจาก CSV และ Text
   - คัดกรองเกรดที่ไม่ผ่าน (F, W, U, ไม่สอบ) เพื่อส่งเข้าคิวลงทะเบียนเรียนใหม่ (P0_RETAKE)

---

## การติดตั้งและการรัน (Getting Started)

### ติดตั้ง Dependencies
```bash
pip install -r requirements.txt
```

### การรัน Unit Tests
```bash
python -m pytest tests/ -v
```

### การรัน Service (FastAPI Port 8500)
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8500 --reload
```

---

## API Endpoints & ตัวอย่าง Request / Response

### 1. Health Check
`GET /health`

**Response (200 OK):**
```json
{
  "ok": true,
  "service": "05_data_integration"
}
```

---

### 2. ดึง Student Context
`GET /context/{student_id}`

**Response (200 OK):**
```json
{
  "student_id": "116610462000-0",
  "name_th": "นายทดสอบ ระบบ",
  "program_id": "CPE-2566",
  "entry_year": 2566,
  "student_year": 4,
  "curriculum_year": 2566,
  "expected_grad_year": 2570,
  "academic_summary": {
    "total_credits_earned": 20,
    "min_total_credits": 143,
    "remaining_total_credits": 123,
    "gpax": 2.55,
    "passed_courses_count": 5,
    "failed_courses_count": 2
  },
  "passed_courses": [
    "01000101-62",
    "04000202-63",
    "C0400011",
    "C0407121",
    "C0407132"
  ],
  "failed_courses": [
    "04000203-63",
    "C0407131"
  ],
  "unlocked_courses": [
    "04000204-62",
    "040603001"
  ],
  "category_progress": [
    {
      "category_id": "1",
      "name": "หมวดวิชาศึกษาทั่วไป",
      "min_credits": 30,
      "passed_credits": 20,
      "remaining_credits": 10,
      "is_completed": false
    }
  ],
  "preferences": {
    "no_early_class": false,
    "free_days": [],
    "max_credits": 21,
    "min_credits": 9,
    "avoid_gaps": true,
    "preferred_teachers": [],
    "campus": "ศูนย์รังสิต"
  }
}
```

---

### 3. ตรวจสอบวิชาบังคับก่อน (Prerequisite Info)
`GET /prereq/{course_code}`

**ตัวอย่าง:** `GET /prereq/040603002` (วิชาโครงสร้างข้อมูล)

**Response (200 OK):**
```json
{
  "course_code": "040603002",
  "direct_prerequisites": [
    "040603001"
  ],
  "all_prerequisites": [
    "040603001"
  ],
  "direct_unlocks": [
    "040603003"
  ],
  "all_unlocks": [
    "040603003",
    "040603004"
  ],
  "critical_path_depth": 2,
  "critical_path_score": 22
}
```

---

### 4. ดึงรายชื่อวิชาที่นักศึกษามีสิทธิ์ลงเรียน (Eligible Courses)
`GET /eligible/{student_id}?term=1/2569`

**Response (200 OK):**
```json
{
  "student_id": "sample",
  "term": "1/2569",
  "eligible_count": 2,
  "eligible_courses": [
    {
      "course_code": "04000204-62",
      "name_th": "แคลคูลัส 2",
      "name_en": "Calculus II",
      "credits": 3,
      "critical_path_score": 0
    },
    {
      "course_code": "040603001",
      "name_th": "การเขียนโปรแกรมคอมพิวเตอร์",
      "name_en": "Computer Programming",
      "credits": 3,
      "critical_path_score": 33
    }
  ]
}
```

---

### 5. ทำความสะอาดข้อมูลรายวิชาและสร้าง Bitmask (Normalize Courses)
`POST /normalize/courses`

**Request Body:**
```json
{
  "courses": [
    {
      "code": " 04000201 - 62 ",
      "name_th": "ฟิสิกส์ 1",
      "credit_detail": "3(2-2-5)",
      "category": "ศึกษาทั่วไป",
      "sections": [
        {
          "section": "01",
          "term": "1/2569",
          "meetings": [
            {
              "day": "จ.",
              "start_min": "09:00",
              "end_min": "12:00"
            }
          ],
          "seat_total": 40,
          "seat_taken": 35
        }
      ],
      "prerequisites": []
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "processed_count": 1,
  "courses": [
    {
      "code": "04000201-62",
      "base_code": "04000201",
      "name_th": "ฟิสิกส์ 1",
      "name_en": "",
      "credits": 3,
      "credit_detail": {
        "credits": 3,
        "lecture": 2,
        "lab": 2,
        "self_study": 5,
        "raw": "3(2-2-5)"
      },
      "category": "ศึกษาทั่วไป",
      "sections": [
        {
          "section": "01",
          "term": "1/2569",
          "slots_mask": 252,
          "slots_binary": "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000011111100",
          "meetings": [
            {
              "day": "จ.",
              "start_min": "09:00",
              "end_min": "12:00",
              "time_str": null,
              "room": null,
              "building": null,
              "meeting_type": "lecture"
            }
          ],
          "teachers": [],
          "seat_total": 40,
          "seat_taken": 35,
          "campus": null
        }
      ],
      "prerequisites": []
    }
  ]
}
```

---

### 6. ตรวจสอบเวลาชนกัน (Clash Check)
`POST /slots/clash-check`

**Request Body:**
```json
{
  "meetings_a": [
    { "day": "จ.", "start_min": "09:00", "end_min": "12:00" }
  ],
  "meetings_b": [
    { "day": "MON", "start_min": "10:30", "end_min": "13:30" }
  ]
}
```

**Response (200 OK):**
```json
{
  "has_clash": true,
  "mask_a": 252,
  "mask_b": 1008,
  "overlap_count": 1,
  "overlaps": [
    {
      "day": "MON",
      "day_th": "จันทร์",
      "overlap_start": "10:30",
      "overlap_end": "12:00",
      "start_min": 630,
      "end_min": 720
    }
  ]
}
```

---

### 7. ค้นหารายวิชาแบบทนต่อการพิมพ์ผิด (Fuzzy Search)
`GET /search/courses?q=ฟิสิก`

**Response (200 OK):**
```json
{
  "query": "ฟิสิก",
  "count": 1,
  "results": [
    {
      "code": "04000201-62",
      "name_th": "ฟิสิกส์ 1",
      "name_en": "Physics I",
      "credits": 3,
      "credit_detail": "3(3-0-6)",
      "category": "ศึกษาทั่วไป",
      "score": 90.0
    }
  ]
}
```
