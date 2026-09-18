# 05 — Data Model (Postgres)

```sql
-- ===== หลักสูตร / รายวิชา =====
CREATE TABLE programs (
  id              TEXT PRIMARY KEY,        -- 'CPE-2566'
  name_th         TEXT NOT NULL,
  faculty         TEXT,
  curriculum_year SMALLINT,                -- ปีหลักสูตร (สำคัญ! กฎต่างกันตามปี)
  total_credits   SMALLINT
);

CREATE TABLE courses (
  code          TEXT PRIMARY KEY,          -- 'ENG101'
  name_th       TEXT NOT NULL,
  name_en       TEXT,
  credits       SMALLINT NOT NULL,
  credit_detail TEXT,                      -- '3(2-2-5)'
  category      TEXT,                      -- general | major | elective
  description   TEXT
);

CREATE TABLE course_prereq (
  course_code   TEXT REFERENCES courses(code),
  prereq_code   TEXT REFERENCES courses(code),
  type          TEXT DEFAULT 'before',     -- before | concurrent
  PRIMARY KEY (course_code, prereq_code)
);

CREATE TABLE program_courses (             -- วิชาในแผนหลักสูตร
  program_id     TEXT REFERENCES programs(id),
  course_code    TEXT REFERENCES courses(code),
  suggested_year SMALLINT,                 -- แนะนำให้เรียนปีไหน
  suggested_term SMALLINT,
  is_required    BOOLEAN DEFAULT TRUE,
  PRIMARY KEY (program_id, course_code)
);

-- ===== ตารางสอน =====
CREATE TABLE sections (
  id            BIGSERIAL PRIMARY KEY,
  course_code   TEXT REFERENCES courses(code),
  section       TEXT NOT NULL,             -- '01'
  term          TEXT NOT NULL,             -- '1/2569'
  slots_mask    BIT(182),                  -- 7 วัน x 26 ช่อง (30 นาที) 08:00-21:00
  teachers      TEXT[],
  seat_total    SMALLINT,
  seat_taken    SMALLINT,
  campus        TEXT,
  is_online     BOOLEAN DEFAULT FALSE,
  source        TEXT,
  fetched_at    TIMESTAMPTZ,
  UNIQUE (course_code, section, term)
);

CREATE TABLE section_meetings (            -- 1 sec มีได้หลายคาบ (บรรยาย + ปฏิบัติ)
  id           BIGSERIAL PRIMARY KEY,
  section_id   BIGINT REFERENCES sections(id) ON DELETE CASCADE,
  day_of_week  SMALLINT,                   -- 0=MON .. 6=SUN
  start_min    SMALLINT,                   -- นาทีจากเที่ยงคืน 540 = 09:00
  end_min      SMALLINT,
  room         TEXT,
  building     TEXT,
  meeting_type TEXT                        -- lecture | lab
);

CREATE TABLE exams (
  section_id BIGINT REFERENCES sections(id) ON DELETE CASCADE,
  exam_type  TEXT,                         -- midterm | final
  exam_date  DATE,
  start_min  SMALLINT,
  end_min    SMALLINT,
  room       TEXT,
  PRIMARY KEY (section_id, exam_type)
);

CREATE TABLE academic_calendar (
  term        TEXT,
  event_type  TEXT,                        -- open | close | add_drop_end | withdraw_end | exam
  event_date  DATE,
  description TEXT
);

-- ===== นักศึกษา =====
CREATE TABLE students (
  id             TEXT PRIMARY KEY,         -- เก็บเป็น hash ถ้าเป็นไปได้
  name_th        TEXT,
  program_id     TEXT REFERENCES programs(id),
  entry_year     SMALLINT,
  gpax           NUMERIC(3,2),
  credits_earned SMALLINT,
  created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE student_courses (             -- ทรานสคริปต์
  student_id  TEXT REFERENCES students(id),
  course_code TEXT REFERENCES courses(code),
  term        TEXT,
  grade       TEXT,                        -- A B+ ... F W I
  passed      BOOLEAN,
  PRIMARY KEY (student_id, course_code, term)
);

CREATE TABLE student_preferences (
  student_id         TEXT PRIMARY KEY REFERENCES students(id),
  no_early_class     BOOLEAN DEFAULT FALSE,  -- ไม่เอาคาบก่อน 09:00
  free_days          SMALLINT[],             -- [4] = อยากว่างศุกร์
  max_credits        SMALLINT DEFAULT 22,
  min_credits        SMALLINT DEFAULT 9,
  avoid_gaps         BOOLEAN DEFAULT TRUE,
  preferred_teachers TEXT[],
  updated_at         TIMESTAMPTZ DEFAULT now()
);

-- ===== แผนการเรียน =====
CREATE TABLE plans (
  id            BIGSERIAL PRIMARY KEY,
  student_id    TEXT REFERENCES students(id),
  term          TEXT,
  name          TEXT,                      -- 'แผน A', 'แผนสำรอง'
  status        TEXT DEFAULT 'draft',      -- draft | saved | submitted
  total_credits SMALLINT,
  score         NUMERIC,                   -- คะแนนจาก solver
  generated_by  TEXT,                      -- manual | auto
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE plan_items (
  plan_id    BIGINT REFERENCES plans(id) ON DELETE CASCADE,
  section_id BIGINT REFERENCES sections(id),
  PRIMARY KEY (plan_id, section_id)
);

CREATE TABLE plan_conflicts (              -- snapshot ผลตรวจล่าสุด
  plan_id    BIGINT REFERENCES plans(id) ON DELETE CASCADE,
  code       TEXT,                         -- C1..C6, W1..W5
  severity   TEXT,                         -- ERROR | WARNING
  detail     JSONB,
  checked_at TIMESTAMPTZ DEFAULT now()
);

-- ===== AI / Log =====
CREATE TABLE chat_sessions (
  id         BIGSERIAL PRIMARY KEY,
  student_id TEXT REFERENCES students(id),
  started_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chat_messages (
  id         BIGSERIAL PRIMARY KEY,
  session_id BIGINT REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role       TEXT,                         -- user | assistant | tool
  content    TEXT,
  intent     TEXT,
  sources    JSONB,                        -- [{title, section, page}]
  tokens_in  INT,
  tokens_out INT,
  latency_ms INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE feedback (
  id          BIGSERIAL PRIMARY KEY,
  student_id  TEXT,
  target_type TEXT,                        -- message | plan
  target_id   BIGINT,
  rating      SMALLINT,                    -- 1 = ชอบ, -1 = ไม่ชอบ
  reason      TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE event_logs (
  id           BIGSERIAL PRIMARY KEY,
  request_id   TEXT,
  student_hash TEXT,                       -- hash ไม่เก็บรหัสจริงใน log
  service      TEXT,
  action       TEXT,
  status       TEXT,
  latency_ms   INT,
  cost_est     NUMERIC(10,6),
  payload      JSONB,
  created_at   TIMESTAMPTZ DEFAULT now()
);

-- ===== INDEX ที่ควรมี =====
CREATE INDEX idx_sections_term    ON sections(term);
CREATE INDEX idx_meetings_day     ON section_meetings(day_of_week, start_min);
CREATE INDEX idx_student_courses  ON student_courses(student_id);
CREATE INDEX idx_logs_created     ON event_logs(created_at DESC);
```

## หมายเหตุการออกแบบ

- `slots_mask BIT(182)` ทำให้เช็คตารางชนเหลือแค่การ AND บิต → เร็วมาก
  แต่ยังต้องเก็บ `section_meetings` ไว้แสดงผลและบอก "ช่วงเวลาที่ทับกันจริง" ให้ผู้ใช้เห็น
- `curriculum_year` สำคัญมาก — นักศึกษาคนละรุ่นใช้ระเบียบ/โครงสร้างหลักสูตรต่างกัน
  เวลาให้ RAG ตอบเรื่องกฎ ต้องกรองด้วยค่านี้เสมอ
- ตารางที่มีข้อมูลส่วนบุคคล (`students`, `student_courses`) ต้องมีนโยบายลบตามคำขอเจ้าของข้อมูล (PDPA)
- เวลาเก็บเป็น "นาทีจากเที่ยงคืน" (int) ไม่เก็บเป็น string — เทียบง่ายและไม่พลาดเรื่อง timezone
