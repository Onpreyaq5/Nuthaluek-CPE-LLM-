# Module 08 — Recommendation, Feedback & Monitoring

โมดูลนี้รับผิดชอบการประกอบผลคำแนะนำจากระบบวางแผนการเรียน การเก็บ event และ feedback การแจ้งเตือน การวิเคราะห์ภาพรวม การส่งออกปฏิทิน และการจัดการข้อมูล analytics ตามหลัก PDPA

> ขอบเขตสำคัญ: โมดูล 08 ไม่ตัดสินว่าตารางเรียนชนหรือไม่ การตรวจ conflict, prerequisite, หน่วยกิต และที่นั่งเป็นหน้าที่ของโมดูล 06 ส่วนข้อความอธิบายมาจากโมดูล 07

## สถานะปัจจุบัน

ส่วนที่พัฒนาเสร็จแล้ว:

- FastAPI service บนพอร์ต `8800`
- Health check และ database readiness check
- Event logging แบบรายการเดียวและแบบ batch
- ป้องกัน event ซ้ำด้วย `event_id`
- รองรับ contract จาก API Gateway เช่น `event` และ `id_hash`
- ตัดข้อมูลส่วนตัวออกจาก nested event payload
- ปฏิเสธรหัสนักศึกษาจริงในช่อง `student_hash`
- Feedback คะแนน `1–5`
- สร้าง review queue อัตโนมัติเมื่อคะแนนไม่เกิน `2`
- Recommendation composer สำหรับรวมผลจากโมดูล 06 และ 07
- Alert A1–A5 และ web notification
- ป้องกันการแจ้งเตือนซ้ำด้วย deduplication key
- Analytics summary สำหรับ dashboard
- Prometheus metrics
- ส่งออกแผนการเรียนเป็นไฟล์ `.ics`
- ลบข้อมูล analytics ของนักศึกษาด้วย `student_hash`
- Celery task สำหรับลบ event log ที่หมดอายุ
- ชุดทดสอบ API และ service จำนวน 10 รายการ

ส่วนที่ต้องเชื่อมต่อเพิ่มเติม:

- ให้โมดูล 02 ส่ง `event_id` ที่คงที่มากับทุก event
- ตกลง endpoint ของโมดูล 05 สำหรับรับ `preference_signal`
- ให้โมดูล 06/07 ส่ง candidate และ explanation ตาม contract
- เพิ่ม Celery worker/beat และ `INTERNAL_API_TOKEN` ใน `docker-compose.yml` โดยเจ้าของไฟล์ส่วนกลาง
- ทำ database migration กลางก่อนใช้งาน production
- Email และ LINE ต้องมี recipient mapping, consent และ secret ก่อนเปิดใช้
- การ export รูปตารางเรียนรอทีมกำหนดรูปแบบและ endpoint

## โครงสร้าง

```text
08_recommendation_feedback/
├── src/
│   ├── api/
│   │   ├── deps.py                 # Internal service authentication
│   │   └── router.py               # API endpoints
│   ├── core/
│   │   ├── config.py               # Environment configuration
│   │   ├── database.py             # SQLAlchemy engine/session
│   │   ├── http.py                 # Request ID และ response/error envelope
│   │   └── metrics.py              # Prometheus metrics
│   ├── models/
│   │   └── entities.py             # Event, feedback, review, notification
│   ├── schemas/
│   │   └── contracts.py            # Pydantic API contracts
│   ├── services/
│   │   ├── alerts.py               # Alert A1–A5
│   │   ├── analytics.py            # Dashboard aggregates
│   │   ├── calendar_export.py      # ICS export
│   │   ├── data_privacy.py         # Delete by student_hash
│   │   ├── events.py               # Event ingestion
│   │   ├── feedback.py             # Feedback และ review queue
│   │   ├── privacy.py              # PII scrubbing
│   │   └── recommendations.py      # Recommendation composer
│   ├── workers/
│   │   ├── celery_app.py
│   │   └── tasks.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   └── test_calendar.py
├── 01_env.txt
├── 02_step.txt
├── 03_process.txt
├── Dockerfile
└── requirements.txt
```

## การติดตั้งและรัน

```bash
cd 08_recommendation_feedback
python -m pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8800 --reload
```

เปิด API documentation ได้ที่:

- Swagger UI: `http://localhost:8800/docs`
- OpenAPI JSON: `http://localhost:8800/openapi.json`
- Health: `http://localhost:8800/health`

หากไม่ได้กำหนด `DATABASE_URL` ระบบ local จะใช้ `sqlite:///./feedback.db` ส่วน Docker Compose ของโปรเจกต์กำหนด PostgreSQL ให้แล้ว

## Environment variables

| ตัวแปร | ค่าเริ่มต้น | หน้าที่ |
|---|---:|---|
| `DATABASE_URL` | `sqlite:///./feedback.db` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379/3` | Celery broker/backend |
| `LOG_LEVEL` | `INFO` | ระดับ application log |
| `INTERNAL_API_TOKEN` | ว่าง | ป้องกัน analytics, alert และ privacy endpoints |
| `CORS_ORIGINS` | `http://localhost:3000` | Origin ที่อนุญาต |
| `NOTIFY_CHANNELS` | `web` | ช่องทางแจ้งเตือนที่เปิดใช้ |
| `LINE_CHANNEL_TOKEN` | ว่าง | Secret สำหรับ LINE ในอนาคต |
| `LOG_RETENTION_DAYS` | `90` | อายุ event log |
| `LOW_SEAT_THRESHOLD` | `5` | เกณฑ์แจ้งเตือนที่นั่งใกล้เต็ม |
| `REVIEW_RATING_THRESHOLD` | `2` | คะแนนสูงสุดที่จะเข้าคิว review |
| `MAX_EVENT_BATCH` | `500` | จำนวน event สูงสุดต่อ batch |

Production ต้องกำหนด `INTERNAL_API_TOKEN` และห้าม commit secret ลง Git

## API endpoints

| Method | Endpoint | หน้าที่ |
|---|---|---|
| `GET` | `/health` | ตรวจว่า process ทำงานอยู่ |
| `GET` | `/ready` | ตรวจการเชื่อมต่อฐานข้อมูล |
| `GET` | `/metrics` | Prometheus metrics |
| `POST` | `/events` | รับ event หนึ่งรายการ |
| `POST` | `/events/batch` | รับ event หลายรายการ สูงสุด 500 |
| `POST` | `/feedback` | รับ analytical feedback |
| `POST` | `/recommendations/compose` | รวม candidates เป็น recommendation output |
| `POST` | `/alerts/evaluate` | ประเมิน Alert A1–A5 |
| `GET` | `/notifications/{student_hash}` | อ่าน web notifications |
| `GET` | `/analytics/summary` | ข้อมูลสรุปสำหรับ dashboard |
| `GET` | `/export/ics/{plan_id}` | ส่งออกแผนเป็น `.ics` |
| `DELETE` | `/privacy/students/{student_hash}` | ลบ analytics ของนักศึกษา |

Endpoint ภายในต่อไปนี้ใช้ header `X-Internal-Token` เมื่อกำหนด `INTERNAL_API_TOKEN`:

- `/alerts/evaluate`
- `/notifications/{student_hash}`
- `/analytics/summary`
- `/privacy/students/{student_hash}`

## ตัวอย่างการส่ง Event Batch

```json
{
  "events": [
    {
      "event_id": "evt-0192",
      "request_id": "req-7ac1",
      "student_hash": "8df1309c43a1e207",
      "service": "02_api_backend",
      "action": "plan.validate",
      "intent": "validate_plan",
      "tools": ["conflicts.check"],
      "latency_ms": 143,
      "tokens_in": 0,
      "tokens_out": 0,
      "cost_est": 0,
      "status": "success",
      "payload": {
        "conflicts": []
      }
    }
  ]
}
```

`event_id` ควรเป็นค่าที่คงที่สำหรับ logical event เดิม เพื่อให้ retry แล้วไม่สร้างข้อมูลซ้ำ

## ตัวอย่าง Feedback

```json
{
  "source_feedback_id": "feedback-1001",
  "request_id": "req-7ac1",
  "student_hash": "8df1309c43a1e207",
  "target_type": "plan",
  "target_id": "12",
  "rating": 2,
  "reason": "มีเรียนเช้าเกินไป",
  "preference_signal": {
    "no_early_class": true
  }
}
```

Feedback คะแนน 1–2 จะถูกเพิ่มเข้า `review_queue` อัตโนมัติ

## Alert codes

| Code | ความหมาย |
|---|---|
| `A1` | ใกล้วันลงทะเบียน 7/3/1 วัน |
| `A2` | ที่นั่งของ section เหลือน้อยกว่าเกณฑ์ |
| `A3` | Section ถูกยกเลิกหรือเปลี่ยนเวลา |
| `A4` | ใกล้วันสุดท้ายของการถอนรายวิชา |
| `A5` | หน่วยกิตในแผนต่ำกว่าเกณฑ์ |

## Export ปฏิทิน

```http
GET /export/ics/12?start_date=2026-06-01&end_date=2026-10-01
```

ระบบอ่านข้อมูลจากตารางกลางแบบ read-only:

- `plans`
- `plan_items`
- `sections`
- `section_meetings`

ไฟล์ที่ได้ใช้ timezone `Asia/Bangkok` และสร้าง weekly recurring event จนถึง `end_date`

## Analytics

`GET /analytics/summary` คืนข้อมูล aggregate เช่น:

- จำนวน event แยกตาม action, status และ service
- P95 latency
- token input/output และค่าใช้จ่ายโดยประมาณ
- ค่าเฉลี่ย feedback และจำนวนคะแนนต่ำ
- จำนวนรายการที่รอ review
- Plan acceptance rate
- คำถามที่ตอบไม่ได้
- Conflict code ที่พบบ่อย

ระบบไม่คืน event รายบุคคลหรือข้อมูลส่วนตัวผ่าน analytics endpoint

## Privacy และ PDPA

- รับเฉพาะ `student_hash` ไม่รับรหัสนักศึกษาจริง
- ลบ sensitive keys เช่น `student_id`, ชื่อ, email, phone, password และ transcript
- Mask รหัสนักศึกษา เบอร์โทรศัพท์ และ email ที่อยู่ในข้อความ
- รองรับการลบข้อมูล analytics ตาม `student_hash`
- Event log มี retention เริ่มต้น 90 วัน
- Transcript และเกรดไม่ควรถูกส่งมายังโมดูลนี้

## การรัน Worker

```bash
celery -A src.workers.celery_app.celery_app worker --loglevel=INFO
```

Task ที่มีอยู่:

- `feedback.purge_expired_event_logs`

การกำหนด schedule และเพิ่ม worker container เป็นหน้าที่ของเจ้าของ `docker-compose.yml`

## การทดสอบ

```bash
python -m pytest -q
```

ผลล่าสุด:

```text
10 passed
```

ชุดทดสอบครอบคลุม:

- Health และ readiness
- Event batch และ idempotency
- PII masking
- การปฏิเสธ raw student ID
- Feedback และ review queue
- Contract alias จาก API Gateway
- Recommendation composer
- Alert A1–A5 และ deduplication
- Internal token
- Privacy deletion
- ICS export

## Disclaimer

ผลลัพธ์ recommendation ทุกชุดมีข้อความต่อไปนี้แนบเสมอ:

> ระบบนี้เป็นเครื่องมือช่วยวางแผนเบื้องต้น ไม่ใช่การยืนยันจากมหาวิทยาลัย โปรดตรวจสอบกับระบบทะเบียนและอาจารย์ที่ปรึกษาก่อนลงทะเบียนจริง
