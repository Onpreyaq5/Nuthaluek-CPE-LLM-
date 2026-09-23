# 03 — AI Router / Agent

ระบบ **จับ intent + เลือก tool + คุม context** สำหรับระบบช่วยวางแผนการเรียน RMUTT  
รันบน **FastAPI** พอร์ต `8100` ภายใน Docker Compose

---

## ภาพรวม

AI Router / Agent คือ "สมองกลาง" ของระบบ ทำหน้าที่ 4 อย่าง:

1. **จำแนก Intent** — เข้าใจว่านักศึกษาต้องการอะไร (2 ชั้น: keyword → LLM)
2. **เลือกและเรียก Tools** — ตัดสินใจว่าจะใช้ service ไหน เรียงลำดับอย่างไร
3. **คุม Context** — จัดการ token budget ของประวัติการสนทนา
4. **ตรวจ Guardrail** — บังคับกฎ domain เช่น "ตารางชนต้องผ่าน engine เท่านั้น"

---

## โครงสร้างไฟล์

```
03_ai_router_agent/
├── src/
│   ├── config.py           # Settings จาก env vars (pydantic-settings)
│   ├── models.py           # Pydantic schemas: RouterRequest, RouterResponse, SSEEvent ...
│   ├── classifier.py       # 2-layer intent classifier (keyword → LLM)
│   ├── tools.py            # Tool Registry: 6 tools → HTTP calls ไปยัง services อื่น
│   ├── context_manager.py  # Token counting (tiktoken) + history trimming
│   ├── guardrails.py       # Hard rules: conflict ต้องผ่าน 06, ระเบียบต้องมี RAG
│   ├── planner.py          # Planner Loop: staged parallel tool execution
│   └── main.py             # FastAPI app: POST /chat (SSE), POST /classify, GET /health
├── 01_env.txt
├── 02_step.txt
├── 03_process.txt
├── Dockerfile
└── requirements.txt
```

---

## Sequence Diagram

### Flow หลัก: POST /chat (SSE Streaming)

```mermaid
sequenceDiagram
    autonumber
    participant U  as Student / User
    participant FE as 01 Web App
    participant BE as 02 API Backend
    participant RT as 03 AI Router ★
    participant LM as LLM API (Gemini/OpenAI)
    participant C4 as 04 Course Data
    participant C5 as 05 Data Integration
    participant C6 as 06 Schedule Engine
    participant C7 as 07 RAG / LLM Engine

    U  ->> FE : พิมพ์ข้อความ / ถามคำถาม
    FE ->> BE : POST /api/v1/chat { message, session_id, student_id }
    BE ->> RT : POST /chat { student_id, message, history }

    Note over RT: ── Layer 1: Keyword Classifier ──
    RT ->> RT : keyword_classify(message)
    alt confidence >= 0.7
        RT ->> BE : SSE: router_result { intent, confidence, source="keyword" }
    else confidence < 0.7
        Note over RT: ── Layer 2: LLM Classifier ──
        RT ->> LM : classify prompt → JSON { intent, confidence, reasoning, slots }
        LM -->> RT : { intent, confidence, reasoning, slots }
        RT ->> BE : SSE: router_result { intent, confidence, source="llm" }
    end

    alt Slot ไม่ครบ (เช่น ไม่มีรหัสวิชา)
        RT ->> BE : SSE: clarify { question, missing_slots }
        BE ->> FE : SSE forward
        FE ->> U  : แสดงคำถามกลับ
    else Slot ครบ → Planner Loop
        Note over RT: ── Planner Loop (MAX_TOOL_STEPS=5) ──

        alt intent = SCHEDULE_CONFLICT
            RT ->> BE : SSE: tool_start { tool: "get_student_context" }
            RT ->> C5 : GET /context/{student_id}
            C5 -->> RT : student profile + transcript
            RT ->> BE : SSE: tool_end { tool, latency_ms }

            RT ->> BE : SSE: tool_start { tool: "check_conflicts" }
            RT ->> C6 : POST /conflicts/check { sections }
            C6 -->> RT : conflicts[] { C1-C6, W1-W5 }
            RT ->> BE : SSE: tool_end { tool, latency_ms }

        else intent = PLAN_GENERATE
            par parallel tools
                RT ->> C5 : GET /context/{student_id}
            end
            par parallel tools
                RT ->> C4 : POST /courses/search { term }
            end
            RT ->> C6 : POST /plans/auto { student_id, term, preferences }
            C6 -->> RT : 3-5 ranked plans (CP-SAT)

        else intent = COURSE_INFO
            RT ->> C4 : POST /courses/search { q, term }
            C4 -->> RT : matching sections + seats

        else intent = CURRICULUM_RULE
            par parallel tools
                RT ->> C5 : GET /context/{student_id}
                RT ->> C7 : POST /knowledge/search { query }
            end
            C7 -->> RT : RAG chunks + citations

        else intent = REGULATION_QA
            RT ->> C7 : POST /knowledge/search { query, top_k=6 }
            C7 -->> RT : RAG chunks + citations

        else intent = GENERAL_CHAT
            Note over RT: ไม่มี tool call → ส่งตรงไป 07
        end

        Note over RT: ── Guardrail Check ──
        alt SCHEDULE_CONFLICT แต่ไม่ได้เรียก check_conflicts
            RT ->> BE : SSE: done { answer: "ไม่สามารถตรวจสอบได้..." }
        else REGULATION_QA แต่ RAG ไม่เจอหลักฐาน
            RT ->> BE : SSE: done { answer: "ไม่พบข้อมูลในระเบียบ..." }
        else ผ่าน Guardrail
            RT ->> BE : SSE: sources { sources: [{title, page}] }
            RT ->> BE : SSE: context_ready { intent, context: {profile, tool_results, history} }
        end
    end

    BE ->> C7 : POST /generate { context, question } (SSE)
    C7 -->> BE : SSE tokens (streamed answer)
    BE -->> FE : SSE forward (token by token)
    FE -->> U  : แสดงคำตอบแบบ streaming + ปุ่ม 👍/👎

    BE ->> BE : log async { intent, latency, tokens, cost_est }
```

---

### Flow ย่อย: Two-Layer Classifier

```mermaid
flowchart TD
    A([รับข้อความจากนักศึกษา]) --> B[Layer 1: Keyword Rules\nนับคะแนน keyword ทุก intent]
    B --> C{confidence\n>= 0.7?}
    C -- ใช่ --> D[ใช้ผล Keyword\nsource = keyword]
    C -- ไม่ใช่ --> E[Layer 2: LLM Classifier\nส่ง prompt → รับ JSON]
    E --> F{LLM\nสำเร็จ?}
    F -- ใช่ --> G[ใช้ผล LLM\nsource = llm]
    F -- ไม่ --> H[Fallback กลับ\nผล Keyword]
    D --> I[ดึง Slots\nterm, course_code, day, time]
    G --> I
    H --> I
    I --> J{Slot\nครบไหม?}
    J -- ครบ --> K([ส่งต่อ Planner Loop])
    J -- ไม่ครบ --> L([SSE: clarify\nถามกลับ 1 คำถาม])
```

---

### Flow ย่อย: Planner Loop (Intent → Tool Map)

```mermaid
flowchart LR
    subgraph INTENT["Intent ที่จำแนกได้"]
        SC[SCHEDULE_CONFLICT]
        PG[PLAN_GENERATE]
        CI[COURSE_INFO]
        CR[CURRICULUM_RULE]
        RQ[REGULATION_QA]
        GC[GENERAL_CHAT]
    end

    subgraph TOOLS["Tools / Services"]
        T5[get_student_context\n→ Module 05]
        T4[search_courses\n→ Module 04]
        T6C[check_conflicts\n→ Module 06]
        T6P[generate_plan\n→ Module 06]
        T7K[search_knowledge\n→ Module 07 RAG]
        T7A[answer_with_llm\n→ Module 07 LLM]
    end

    SC --> T5
    SC --> T6C
    PG --> T5
    PG --> T4
    PG --> T6P
    CI --> T4
    CR --> T5
    CR --> T7K
    RQ --> T7K
    GC --> T7A
```

---

## Intents ที่รองรับ

| Intent | ตัวอย่างคำถาม | Tools ที่เรียก |
|---|---|---|
| `SCHEDULE_CONFLICT` | "ลงวิชา CPE101 ชนไหม?" | `get_student_context` → `check_conflicts` |
| `PLAN_GENERATE` | "จัดตารางเทอม 1/2569 ให้หน่อย" | `get_student_context` → `search_courses` → `generate_plan` |
| `COURSE_INFO` | "CPE201 เปิดกี่ section?" | `search_courses` |
| `CURRICULUM_RULE` | "เหลืออีกกี่หน่วยกิตถึงจะจบ?" | `get_student_context` + `search_knowledge` |
| `REGULATION_QA` | "ถอนรายวิชาได้ถึงเมื่อไหร่?" | `search_knowledge` (RAG) |
| `GENERAL_CHAT` | "สวัสดี / ขอบคุณ" | ส่งตรงไป Module 07 |

---

## SSE Event Types

ทุก response จาก `/chat` เป็น **Server-Sent Events** สตรีมออกมาตามลำดับนี้:

```
router_result   → intent, confidence, reasoning, slots
tool_start      → ชื่อ tool ที่กำลังจะเรียก
tool_end        → ชื่อ tool, success, latency_ms
sources         → รายการอ้างอิงจาก RAG (ถ้ามี)
context_ready   → context ก้อนรวมส่งต่อ Module 07
done            → latency_ms รวม
─── หรือ ───
clarify         → question กลับถามนักศึกษา (slot ไม่ครบ)
error           → ข้อความ error
```

---

## Guardrails

| กฎ | เงื่อนไข | พฤติกรรม |
|---|---|---|
| **G1** | `SCHEDULE_CONFLICT` แต่ไม่ได้เรียก `check_conflicts` | ปฏิเสธตอบ → แจ้งให้ระบุรหัสวิชา |
| **G2** | `REGULATION_QA` / `CURRICULUM_RULE` แต่ RAG ไม่มี chunk | ปฏิเสธตอบ → แนะนำติดต่อ สวท. |

> หลักการ: **LLM ห้ามเดาตัวเลขเวลาหรือระเบียบโดยไม่มีหลักฐาน**

---

## API Endpoints

| Method | Path | คำอธิบาย |
|---|---|---|
| `GET` | `/health` | Health check (Docker HEALTHCHECK) |
| `POST` | `/chat` | เส้นหลัก — SSE streaming |
| `POST` | `/classify` | Debug: จำแนก intent เท่านั้น (ไม่เรียก tool) |

### ตัวอย่าง Request Body (POST /chat)

```json
{
  "student_id": "65010001",
  "message": "ลง CPE101 กับ CPE201 ชนไหมครับ",
  "session_id": "sess_abc123",
  "history": [
    { "role": "user",      "content": "สวัสดี" },
    { "role": "assistant", "content": "สวัสดีครับ มีอะไรให้ช่วยไหม" }
  ]
}
```

### ตัวอย่าง SSE Response Stream

```
event: router_result
data: {"intent":"SCHEDULE_CONFLICT","confidence":0.88,"source":"keyword","slots":{"course_codes":["CPE101","CPE201"]}}

event: tool_start
data: {"tool":"get_student_context"}

event: tool_end
data: {"tool":"get_student_context","success":true,"latency_ms":45}

event: tool_start
data: {"tool":"check_conflicts"}

event: tool_end
data: {"tool":"check_conflicts","success":true,"latency_ms":120}

event: context_ready
data: {"intent":"SCHEDULE_CONFLICT","context":{...}}

event: done
data: {"latency_ms":215}
```

---

## Environment Variables

| Variable | Default | คำอธิบาย |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini` / `openai` / `anthropic` |
| `LLM_API_KEY` | — | API key (ห้าม commit) |
| `LLM_MODEL` | `gemini-flash-lite-latest` | ชื่อโมเดลที่ใช้ classify |
| `LOCAL_MODEL_URL` | `http://local_ai:8300` | โมเดลในเครื่อง |
| `COURSE_DATA_URL` | `http://course_data:8400` | Module 04 |
| `DATA_INTEGRATION_URL` | `http://data_integration:8500` | Module 05 |
| `SCHEDULE_ENGINE_URL` | `http://schedule_engine:8600` | Module 06 |
| `RAG_LLM_URL` | `http://rag_llm:8700` | Module 07 |
| `MAX_TOOL_STEPS` | `5` | จำนวน tool call สูงสุดต่อ request |
| `MAX_CONTEXT_TOKENS` | `4000` | token budget ของ history |
| `TOOL_TIMEOUT_S` | `8.0` | timeout ต่อ tool call (วินาที) |
| `CONFIDENCE_THRESHOLD` | `0.7` | ค่าต่ำสุดที่ยอมรับจาก keyword layer |

---

## รันแบบ Standalone (ทดสอบโดยไม่มี services อื่น)

```bash
# 1. ติดตั้ง dependencies
cd 03_ai_router_agent
pip install -r requirements.txt

# 2. ตั้งค่า env
cp ../.env.example .env
#    แก้ LLM_PROVIDER, LLM_API_KEY, LLM_MODEL

# 3. รัน service
uvicorn src.main:app --host 0.0.0.0 --port 8100 --reload

# 4. ทดสอบ classify (ไม่เรียก tool)
curl -X POST http://localhost:8100/classify \
  -H "Content-Type: application/json" \
  -d '{"student_id":"test","message":"CPE101 ชนไหม","session_id":"s1","history":[]}'

# 5. health check
curl http://localhost:8100/health
```

---

## รันกับ Docker Compose (ระบบเต็ม)

```bash
# จาก root ของโปรเจกต์
docker compose up -d --build ai_router_agent

# ดู log
docker compose logs -f ai_router_agent
```

---

## ความสัมพันธ์กับ DL-06

| Concept | DL-06 (ต้นแบบ) | Module นี้ (ปรับเพิ่ม) |
|---|---|---|
| Two-layer classification | LLM ก่อน → keyword fallback | **Keyword ก่อน** → LLM เฉพาะเมื่อ conf < 0.7 |
| Structured JSON output | ✅ | ✅ `{ intent, confidence, reasoning, slots }` |
| Context window (tiktoken) | ✅ | ✅ + เพิ่ม plan_draft และ student profile |
| Routing | 3 routes (General/RAG/Local) | **6 intents** → 6 tool plans |
| Tool calling | abstract | **Named tool registry** 6 tools → service URLs |
| Planner loop | ไม่มี | ✅ `while step < MAX_TOOL_STEPS` (staged parallel) |
| Slot filling | ไม่มี | ✅ term, course_code, day, time + ask-back |
| Guardrails | กล่าวถึงทั่วไป | ✅ G1 conflict, G2 RAG evidence |
| SSE output format | กล่าวถึงทั่วไป | ✅ typed events: tool_start/end/sources/done |
| PDPA | ไม่มี | ✅ student hash ใน log |

---

> **เจ้าของ Module**: ใส่ชื่อใน `01_env.txt`  
> **Port**: 8100  
> **Sprint**: สัปดาห์ที่ 8 (ดู `00_docs/03_flow.md`)
