# แผนแก้ไข 05_data_integration ให้เข้ากับ 02/03 — แก้ที่ 05 เท่านั้น

**สำหรับ:** AI coding assistant ที่จะแก้โค้ด `05_data_integration`
**โค้ดอ้างอิง:** `Onpreyaq5/Nuthaluek-CPE-LLM-`, branch `feat/data-integration`, โฟลเดอร์
`ProJ-RMUTT-Planner/05_data_integration`

**กติกาเหล็ก (ห้ามฝ่าฝืน):**
> `02_api_backend` (branch `feat/api-backend`) และ `03_ai_router_agent` (branch `feat/ai-router`)
> **คือโครงหลักของระบบ ห้ามแก้ไข field, endpoint, schema, หรือพฤติกรรมของ 02/03 เด็ดขาด**
> ทุกจุดที่ไม่ตรงกัน **ต้องแก้ที่ 05_data_integration เท่านั้น** ให้ 05 ปรับตัวเข้าหาสัญญาที่ 02/03
> เรียกใช้อยู่จริงในโค้ดปัจจุบันของทั้งสองฝั่ง (ไม่ใช่เดาจากเอกสาร)
> ห้ามติดลายน้ำ AI ใดๆ หรือ Contributor ใดๆ เด็ดขาด

**สถานะการตรวจสอบ:** ทุกจุดในไฟล์นี้ยืนยันด้วยการรันโค้ดจริงของ 05 (ไม่ใช่การอ่านแล้วเดา) รวมถึงรันด้วย
ไฟล์ตัวอย่างจริงที่ 05 เองแนบมาใน `tests/fixtures/graduate_check_sample.html` — สคริปต์ทดสอบอยู่ที่
`run_05_contract_test.py` ในโฟลเดอร์เดียวกับไฟล์นี้ (`_compat_check/`) รันซ้ำได้ด้วย
`.venv\Scripts\python run_05_contract_test.py` — ผลลัพธ์เต็มอยู่ที่ `out_05.txt`

02 มีอยู่ **2 โหมด** ในการคุยกับ 05 (`ADAPTER_05=http` หรือ `ADAPTER_05=inprocess`) — ปัญหาที่เจอกระทบ
คนละจุดกัน ไฟล์นี้ครอบคลุมทั้งสองโหมด

---

## ปัญหาที่ 1 — `GET /context/{id}` (path ที่ 03 เรียกจริง) shape ผิดเกือบทั้งหมด

### หลักฐานจากการรันจริง

ยิง `GET /context/sample` เข้า 05 จริง ได้ top-level keys:
```
academic_summary, category_progress, curriculum_year, entry_year, expected_grad_year,
failed_courses, name_th, passed_courses, preferences, program_id, student_id,
student_year, unlocked_courses
```
แต่ `StudentContext` ที่ 02/03/06/07 ใช้ร่วมกัน (`02-api-backend-integration-reference.md` หัวข้อ 8,
และ `02_api_backend/src/adapters/interfaces.py::StudentContext`) ต้องการ:
```
student_id, id_hash, program_id, program_name, curriculum_year, year_level,
credits_earned, credits_remaining, gpax, completed_course_codes, preferences
```

field ที่ต้องการแต่ 05 ไม่มี: `id_hash, program_name, year_level, credits_earned, credits_remaining,
gpax(อยู่แต่ซ้อนใน academic_summary ไม่ได้อยู่ระดับบนสุด), completed_course_codes`

**ผลกระทบ:** `03_ai_router_agent/src/tools.py::get_student_context()` คืน raw dict ไม่ validate จึงไม่
error ทันที แต่ downstream ทุกจุดที่คาดหวัง field ตามสัญญา (guardrail, `context_manager.py`, การกรอง RAG
ด้วย `curriculum_year`/`program_id` ใน 07) จะอ่านไม่เจอ ได้ `None`/`missing` เงียบๆ

### วิธีแก้ (แก้ที่ 05 — เพิ่ม field แบบ additive ใน `StudentContext.to_dict()`)

แก้ที่ `src/student_context.py` — **ห้ามลบ field เดิมที่ 05 มีอยู่แล้ว** (เผื่อมีโค้ดอื่นใน 05 พึ่งอยู่) แค่
เพิ่ม field ที่ 02/03 ต้องการเข้าไปด้วย:

```diff
     def to_dict(self) -> dict[str, Any]:
+        preferences_dict = self.preferences.to_dict()
+        preferences_dict["free_days"] = [
+            ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][d]
+            for d in self.preferences.free_days
+            if 0 <= d <= 6
+        ]  # 02/03/07 ใช้ free_days เป็นรหัสวัน MON..SUN ไม่ใช่ตัวเลข 0-6 แบบที่ 05 เก็บภายใน
+
         return {
             "student_id": self.profile.student_id,
+            "id_hash": self.profile.student_id,  # 05 ไม่รู้จัก hashing จริง (อยู่ที่ 02) — แต่ในทางปฏิบัติ
+                                                  # student_id ที่ 02/03 ส่งมาให้ 05 ก็เป็นค่า hash แล้วอยู่แล้ว
+                                                  # (03's RouterRequest.student_id: "synthetic_hash_only")
             "name_th": self.profile.name_th,
             "program_id": self.profile.program_id,
+            "program_name": _PROGRAM_NAMES.get(self.profile.program_id, self.profile.program_id),
             "entry_year": self.profile.entry_year,
             "student_year": self.profile.student_year,
+            "year_level": self.profile.student_year,  # alias ชื่อที่ 02/03 ใช้จริง
             "curriculum_year": self.profile.curriculum_year,
             "expected_grad_year": self.expected_grad_year,
+            "credits_earned": self.total_credits_earned,       # alias ระดับบนสุดตามสัญญา 02/03
+            "credits_remaining": self.remaining_total_credits,  # alias ระดับบนสุดตามสัญญา 02/03
+            "gpax": self.gpax,                                  # alias ระดับบนสุด (เดิมมีแค่ในซ้อน academic_summary)
             "academic_summary": {
                 "total_credits_earned": self.total_credits_earned,
                 "min_total_credits": self.min_total_credits,
                 "remaining_total_credits": self.remaining_total_credits,
                 "gpax": self.gpax,
                 "passed_courses_count": len(self.passed_courses),
                 "failed_courses_count": len(self.failed_courses),
             },
             "passed_courses": self.passed_courses,
+            "completed_course_codes": self.passed_courses,  # alias ชื่อที่ 02/03 ใช้จริง
             "failed_courses": self.failed_courses,
             "unlocked_courses": self.unlocked_courses,
             "category_progress": [c.to_dict() for c in self.category_progress],
-            "preferences": self.preferences.to_dict(),
+            "preferences": preferences_dict,
         }
```

เพิ่ม constant ไว้ท้ายไฟล์ (หรือต้นไฟล์ก็ได้):
```python
_PROGRAM_NAMES = {
    "CPE-2566": "วิศวกรรมคอมพิวเตอร์",
    # เพิ่ม program_id อื่นถ้ามีในอนาคต — ถ้าไม่รู้จัก จะ fallback คืน program_id ตัวมันเองแทน ไม่ crash
}
```

---

## ปัญหาที่ 2 — path ที่ 02 เรียกจริง (โหมด `ADAPTER_05=http`) ไม่มีอยู่จริงใน 05 → 404 ทั้ง 3 endpoint

### หลักฐานจากการรันจริง

`02_api_backend/src/adapters/http/student_data.py` (`HttpStudentData`) เรียก 3 path นี้ตรงๆ:
```
GET  {STUDENT_DATA_URL}/students/{student_id}/context
GET  {STUDENT_DATA_URL}/students/{student_id}/transcript
POST {STUDENT_DATA_URL}/import/graduate-check   (Content-Type: text/html, body = raw bytes)
```
ยิงทั้ง 3 path เข้า 05 จริง **ได้ 404 ทั้งหมด** — 05 ไม่มี route พวกนี้เลย (มีแต่ `/context/{id}`,
`/transcript/parse` ซึ่งคนละความหมาย, ไม่มี import endpoint เลย)

### วิธีแก้ (แก้ที่ 05 — เพิ่ม route ใหม่ 3 เส้นทางใน `src/main.py`)

```python
# src/main.py — เพิ่มท้ายไฟล์ (หรือต่อจาก endpoint /context/{student_id} เดิม)
from fastapi import Request  # เพิ่มเข้า import เดิมของ fastapi ถ้ายังไม่มี


@app.get("/students/{student_id}/context")
def get_student_context_for_02(student_id: str):
    """Alias ของ /context/{id} — path นี้คือของจริงที่ 02_api_backend/src/adapters/http/student_data.py
    เรียก (ต่างจาก path ที่ 03 เรียก) ใช้ handler เดียวกันเป๊ะ ไม่ให้ logic แยกกันสองที่"""
    return get_student_context(student_id)


@app.get("/students/{student_id}/transcript")
def get_student_transcript_for_02(student_id: str):
    """สร้าง TranscriptResponse-shaped output ({courses, credits_by_category}) จาก context
    ที่มีอยู่แล้วในหน่วยความจำ ตามสัญญาที่ 02's schemas/students.py::TranscriptResponse ต้องการ"""
    norm_id = student_id.strip()
    ctx = student_contexts.get(norm_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูลนักศึกษารหัส {norm_id}")
    courses = [
        {
            "course_code": code,
            "course_name_th": (course_index.courses_by_code.get(code).name_th
                                if course_index.courses_by_code.get(code) else ""),
            "credits": (course_index.courses_by_code.get(code).credits
                        if course_index.courses_by_code.get(code) else 0),
            "grade": "ผ่าน" if code in ctx.passed_courses else "ไม่ผ่าน",
            "term": "1/2569",  # 05 ไม่เก็บเทอมที่ลงจริงต่อวิชาในโครงสร้างปัจจุบัน — PLACEHOLDER
                               # ทำเครื่องหมายไว้ให้ทีม 05 เติมข้อมูลจริงทีหลังถ้าต้องใช้ term ที่แม่นยำ
        }
        for code in (ctx.passed_courses + ctx.failed_courses)
    ]
    credits_by_category = {c.category_id: c.passed_credits for c in ctx.category_progress}
    return {"courses": courses, "credits_by_category": credits_by_category}


@app.post("/import/graduate-check")
async def import_graduate_check_http(request: Request):
    """เวอร์ชัน HTTP ของ import_graduate_check — ให้ผลตรงกับที่ 02's
    InprocessStudentData.import_graduate_check() คำนวณตอนใช้ ADAPTER_05=inprocess ทุกประการ
    (เรียกฟังก์ชันร่วม _build_import_result() ด้านล่าง กันโค้ดสองชุดเพี้ยนจากกัน)"""
    raw = await request.body()
    audit = parse_graduate_check(raw)
    return _build_import_result(audit)


def _build_import_result(audit) -> dict:
    """คำนวณผลลัพธ์ shape เดียวกับ 02's schemas/students.py::ImportResult
    ({imported_courses, retake_required, credits_remaining, warnings})
    ใช้ร่วมกันทั้ง path HTTP นี้ และเป็นจุดอ้างอิงเดียวที่ 02's inprocess adapter เรียกไปเทียบด้วย"""
    plan_input = build_plan_input(audit)
    return {
        "imported_courses": len(audit.all_courses()),
        "retake_required": [course.code for _, course in audit.failed_courses()],
        "credits_remaining": plan_input.remaining_total or 0,
        "warnings": [],
    }
```

**หมายเหตุสำคัญ:** `_build_import_result()` ยังมี `plan_input.remaining_total or 0` เหมือนเดิม — เพราะ
ปัญหาที่ 3 (ด้านล่าง) แก้ที่ต้นตอ (`build_plan_input()`) แล้ว `remaining_total` จะไม่เป็น `None` อีกต่อไป
เมื่อ `min_total_credits` รู้ค่า จึงไม่ต้องแก้บรรทัดนี้ซ้ำสองที่

---

## ปัญหาที่ 3 — `credits_remaining` รายงานเป็น 0 ปลอม เวลา parser หาแถวสรุปรวมไม่เจอ

### หลักฐานจากการรันจริง (ใช้ไฟล์ตัวอย่างที่ 05 เองแนบมา)

รัน `parse_graduate_check()` กับ `tests/fixtures/graduate_check_sample.html` (ไฟล์ตัวอย่างของ 05 เอง):
```
min_total_credits: 143
total_passed_credits: None   <-- parser หาแถว "รวม หน่วยกิตที่ผ่าน" ระดับบนสุดไม่เจอในหน้านี้
```
`degree_plan.py::build_plan_input()` เขียนไว้ว่า:
```python
remaining_total = None
if audit.min_total_credits is not None and audit.total_passed_credits is not None:
    remaining_total = max(audit.min_total_credits - audit.total_passed_credits, 0)
```
เพราะ `total_passed_credits is None` เงื่อนไขไม่ผ่าน → `remaining_total = None` เสมอ

แล้ว 02's `InprocessStudentData.import_graduate_check()` เขียนไว้ว่า `credits_remaining =
plan_input.remaining_total or 0` — **`None or 0` กลายเป็น `0`** ผลคือระบบรายงานว่า "เหลืออีก 0 หน่วยกิต"
(แปลว่าใกล้จบแล้ว) ทั้งที่ความจริงคือ "ไม่รู้ข้อมูล เพราะ parser หาแถวสรุปไม่เจอ" — ยืนยันด้วยการรันจริง
ได้ `credits_remaining: 0` ตรงตามที่คาดจากการไล่โค้ด

**อันตราย:** นี่คือข้อมูลที่ผู้ใช้จะเชื่อโดยตรงหลังอัปโหลด transcript ("เหลืออีก 0 หน่วยกิต" ทำให้เข้าใจผิด
ว่าใกล้จบการศึกษา)

### วิธีแก้ (แก้ที่ 05 เท่านั้น — ใช้ fallback แบบเดียวกับที่ `student_context.py` ทำอยู่แล้วในไฟล์เดียวกันของ 05)

`05/src/student_context.py::build_student_context_from_audit()` มี fallback ที่ถูกต้องอยู่แล้วสำหรับ
สถานการณ์เดียวกันนี้เป๊ะ (บรรทัด `earned_tot = audit.total_passed_credits; if earned_tot is None: ...`)
— แค่ยังไม่ได้เอามาใช้ใน `degree_plan.py` เท่านั้นเอง เอา pattern เดียวกันมาใส่:

```diff
 def build_plan_input(
     audit: DegreeAudit,
     search_rows: list | None = None,
     prereq_dag: Any | None = None,
 ) -> DegreePlanInput:
     cands = build_candidates(audit, prereq_dag=prereq_dag)
     term = None
     if search_rows:
         attach_open_sections(cands, search_rows)
         term = next((r.term for r in search_rows if r.term), None)
+
+    # เดิม: ถ้า audit.total_passed_credits เป็น None (parser หาแถวสรุปรวมไม่เจอ) จะปล่อย
+    # remaining_total เป็น None แล้วผู้เรียก (02's inprocess adapter) ทำ `or 0` จนกลายเป็น
+    # "เหลือ 0 หน่วยกิต" ปลอม — ใช้ fallback เดียวกับ student_context.py::build_student_context_from_audit()
+    # เพื่อไม่ให้ earned_credits เป็น None โดยไม่จำเป็น
+    earned_credits = audit.total_passed_credits
+    if earned_credits is None:
+        top_cats = [c for c in audit.categories if c.depth == 1 and c.passed_credits is not None]
+        earned_credits = (
+            sum(c.passed_credits for c in top_cats) if top_cats
+            else sum(c.credits for c in audit.all_courses() if c.passed)
+        )
+
     remaining_total = None
-    if audit.min_total_credits is not None and audit.total_passed_credits is not None:
-        remaining_total = max(audit.min_total_credits - audit.total_passed_credits, 0)
+    if audit.min_total_credits is not None:
+        remaining_total = max(audit.min_total_credits - earned_credits, 0)
     return DegreePlanInput(
         student_id=audit.student_id,
         term=term,
         min_total_credits=audit.min_total_credits,
-        passed_credits=audit.total_passed_credits,
+        passed_credits=earned_credits,
         remaining_total=remaining_total,
         categories=audit.remaining_by_category(),
         candidates=cands,
     )
```

ผลคือ `remaining_total` จะเป็น `None` ก็ต่อเมื่อ `min_total_credits` เองก็ไม่รู้ค่าจริงๆ เท่านั้น (สถานการณ์
ที่แทบไม่เกิดเพราะ 143 เป็นค่ามาตรฐานที่ parser ควรหาเจอเสมอ) — ไม่มีวันปล่อยให้ "หาแถวสรุปรวมไม่เจอ" เงียบๆ
กลายเป็น "0 หน่วยกิต" อีกต่อไป

---

## Checklist สรุป (ไฟล์ที่ต้องแก้ใน 05 ทั้งหมด)

- [ ] `src/student_context.py` — เพิ่ม field alias ใน `StudentContext.to_dict()` (แก้ปัญหาที่ 1) +
      เพิ่ม constant `_PROGRAM_NAMES`
- [ ] `src/main.py` — เพิ่ม 3 route ใหม่ (`/students/{id}/context`, `/students/{id}/transcript`,
      `/import/graduate-check`) + ฟังก์ชัน `_build_import_result()` (แก้ปัญหาที่ 2)
- [ ] `src/degree_plan.py::build_plan_input()` — เพิ่ม fallback คำนวณ `earned_credits` (แก้ปัญหาที่ 3)
- [ ] เพิ่ม test ใหม่ใน `tests/test_api.py` ยิง `POST /import/graduate-check` ด้วย
      `graduate_check_sample.html` แล้ว assert ว่า `credits_remaining != 0` (กัน regression ของปัญหาที่ 3
      โดยเฉพาะ เพราะไฟล์ตัวอย่างนี้เป็นเคสที่เคยพังจริง)

## จุดที่ต้องระวัง

- `/students/{id}/transcript` ที่เพิ่มใหม่ใส่ `"term": "1/2569"` แบบ hardcode ไว้ชั่วคราว (05 ไม่ได้เก็บ
  เทอมที่ลงจริงต่อวิชาในโครงสร้างข้อมูลปัจจุบัน) ถ้าต้องใช้ term ที่แม่นยำต่อรายวิชาจริง ต้องปรับ
  `DegreeAudit`/`CourseRow` ให้เก็บ term มาจาก `Attempt.term` ที่มีอยู่แล้วในโครงสร้าง (`CourseRow.attempts:
  list[Attempt]`, แต่ละ `Attempt` มี `term` อยู่แล้ว) — ไม่ใช่งานใหญ่แต่ไม่ได้ทำในไฟล์นี้เพราะไม่มีหลักฐาน
  ว่า 07/01 ต้องการ term ที่แม่นยำระดับนี้จริง
- `program_name` แก้แบบ hardcode dict เล็กๆ ไว้ก่อน เพราะ 05 ไม่มีแหล่งข้อมูลชื่อหลักสูตรแบบเป็นทางการ
  ถ้ามีหลายหลักสูตรในระบบจริงควรขยาย `_PROGRAM_NAMES` หรือเปลี่ยนเป็นดึงจากไฟล์ config แทน
