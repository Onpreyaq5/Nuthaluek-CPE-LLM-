# TradeRAG — คู่มือระดับโค้ด

ส่วนโปรแกรมของ **LAB 3 (DL-05)** — ดูภาพรวมและเอกสารประกอบที่ [../README.md](../README.md)

## วิธีรัน

```
ดับเบิลคลิก index.html
```

ไม่ต้อง `npm install` ไม่ต้องมีเซิร์ฟเวอร์ ไม่ต้องใช้ API Key
สคริปต์ทั้งหมดเป็น classic script (ไม่ใช่ ES module) จึงเปิดจาก `file://` ได้โดยตรง
และทำงานได้บน htmlpreview.github.io

---

## ลำดับการโหลดสคริปต์

ลำดับใน `index.html` สำคัญ เพราะแต่ละโมดูลพึ่งพาโมดูลก่อนหน้าผ่าน `window`

```
config.js            →  RAG_CONFIG, TRADING_SYNONYMS, SAFETY_PATTERNS
data-basic.js        →  TRADING_KB (ต่อท้าย)
data-advanced.js     →  TRADING_KB (ต่อท้าย)
rag-normalize.js     →  RagNormalize
rag-chunk.js         →  RagChunk        ใช้ RagNormalize
rag-index.js         →  RagIndex        ใช้ RagNormalize
rag-query.js         →  RagQuery        ใช้ RagNormalize + TRADING_SYNONYMS
rag-retrieve.js      →  RagRetrieve     ใช้ RagIndex
rag-rerank.js        →  RagRerank       ใช้ RagIndex.idfOf
rag-generate.js      →  RagGenerate     ใช้ RagNormalize
rag-pipeline.js      →  RagPipeline     ต่อทุกอย่างเข้าด้วยกัน
rag-eval.js          →  RagEval         ใช้ RagPipeline
problems.js          →  RagProblems
usecases.js          →  RagUseCases
mindmap.js           →  RagMindmap
app.js               →  ตัวควบคุมหน้าจอ
```

---

## หน้าที่ของแต่ละไฟล์

### ชั้นข้อมูล

| ไฟล์ | หน้าที่ |
|------|---------|
| `config.js` | พารามิเตอร์ RAG ทุกตัว, พจนานุกรมคำพ้อง 47 กลุ่ม, รูปแบบคำถามที่ต้องบล็อก 17 แบบ |
| `data-basic.js` | ฐานความรู้ชั้นเบื้องต้น 6 หมวด |
| `data-advanced.js` | ฐานความรู้ชั้นเทคนิคขั้นสูง 4 หมวด |

**โครงสร้างเอกสาร 1 รายการ**

```js
{
  id: "I02",                       // รหัสใช้อ้างอิงในคำตอบ
  cat: "อินดิเคเตอร์",              // หมวด ใช้กรอง metadata
  level: "ขั้นกลาง",                // ระดับ ใช้กรอง metadata
  tags: ["rsi", "overbought"],     // ใช้ boost ตอน rerank
  q: "RSI คืออะไร ใช้อย่างไร",      // คำถามหลัก
  alt: ["rsi คืออะไร", "ดัชนีกำลังสัมพัทธ์", ...],  // ลำดับคู่เข้าดัชนี ลำดับคี่กันไว้ทดสอบ
  a: "...",                        // คำตอบ
  updated: "2026-01"               // เดือนที่ทบทวน ใช้เตือนข้อมูลเก่า
}
```

### ชั้นประมวลผล

| ไฟล์ | ฟังก์ชันสำคัญ | แก้ปัญหาข้อ |
|------|--------------|-------------|
| `rag-normalize.js` | `normalizeText()`, `tokenize()`, `dedupe()`, `splitAlt()` | 01, 03, 09 |
| `rag-chunk.js` | `splitByStructure()`, `splitBySize()`, `buildChunks()` | 02 |
| `rag-index.js` | `build()`, `denseSearch()`, `bm25Search()`, `idfOf()` | 03, 05, 08 |
| `rag-query.js` | `expandSynonyms()`, `multiQuery()`, `transform()` | 03, 04 |
| `rag-retrieve.js` | `retrieve()`, `rrfFuse()`, `passFilter()` | 05, 05.1, 07 |
| `rag-rerank.js` | `rerank()`, `coverage()`, `titleMatch()`, `exactTermMatch()` | 06, 08 |
| `rag-generate.js` | `safetyCheck()`, `generate()`, `faithfulness()`, `callLLM()` | 08, 10 |
| `rag-pipeline.js` | `buildIndex()`, `ask()`, `askWithLLM()` | ต่อทุกขั้น + เก็บ trace |
| `rag-eval.js` | `buildGoldenSet()`, `run()`, `runAblation()`, `runChunkStudy()` | 09 |

### ชั้นแสดงผล

| ไฟล์ | หน้าที่ |
|------|---------|
| `problems.js` | นิยามปัญหา 11 ข้อ + `run()` ที่รันจริงเพื่อเทียบก่อน/หลังแก้ ใช้ `withConfig()` ที่คืนค่าเดิมเสมอด้วย `finally` |
| `usecases.js` | ข้อมูล Use Case 9 ตัว + ตัวสร้าง Use Case Diagram เป็น SVG |
| `mindmap.js` | ตัวสร้าง Mind Map เป็น SVG ด้วยอัลกอริทึม Horizontal Tree |
| `app.js` | ควบคุมทุกแท็บ ผูก event บันทึกค่าลง localStorage |
| `style.css` | ธีมพื้นเข้ม ขึ้นเขียว ลงแดง รองรับจอมือถือ |

---

## แนวคิดหลัก 3 ข้อที่ควรรู้ก่อนอ่านโค้ด

### 1. ตัดคำภาษาไทยด้วย character n-gram

ภาษาไทยเขียนติดกันไม่มีช่องว่าง จึงไม่มีทางตัดคำได้ถูกโดยไม่ใช้พจนานุกรม
ระบบเลี่ยงปัญหานี้ด้วยการตัดเป็นชิ้นละ 2–3 ตัวอักษร

```
"แนวรับ" → แน, นว, วร, รับ, แนว, นวร, วรับ
```

ส่วนคำภาษาอังกฤษและตัวเลขตัดเป็นคำตรง ๆ เพราะมีช่องว่างคั่นอยู่แล้ว
โค้ดอยู่ที่ `rag-normalize.js → tokenize()`

### 2. คะแนน 2 ตัวที่ต้องไม่สับสนกัน

| ค่า | ตอบคำถามว่า | ใช้ทำอะไร | คำนวณเมื่อไหร่ |
|-----|-------------|-----------|---------------|
| `score` | ชิ้นไหนดีที่สุดในกลุ่มที่ค้นมาได้ | เรียงลำดับผลลัพธ์ | เฉพาะเมื่อเปิด rerank |
| `grounding` | หลักฐานดีพอจะตอบหรือยัง | ตัดสินว่าจะตอบหรือปฏิเสธ | **เสมอ** |

`grounding` ต้องคำนวณเสมอ เพื่อให้ด่านกัน Hallucination ไม่หายไปเมื่อผู้ใช้ปิด Re-ranking
โค้ดอยู่ที่ `rag-rerank.js → rerank()`

### 3. รายการค้นหาแยกตามแหล่งที่มา

`rag-retrieve.js` ไม่ได้ยัด token ทั้งหมดลงถุงเดียว แต่แยกเป็นรายการตามความน่าเชื่อถือ

| รายการ | ที่มา | น้ำหนัก |
|--------|------|---------|
| คำถามเดิม | ผู้ใช้พิมพ์เอง | 1.00 |
| คำพ้องล้วน ๆ | พจนานุกรมที่คัดมาเอง | 0.90 |
| Multi-Query | ระบบสร้างเองด้วยกฎ | 0.45 |

แล้วรวมด้วย RRF ที่รองรับน้ำหนัก

```
score(d) = Σ  w_i / (60 + rank_i(d))
```

**สำคัญ:** รายการคำพ้องต้องมาจากคำพ้องเท่านั้น ห้ามผสมคำถามเดิม
มิฉะนั้นอันดับจะถูกคำถามเดิมครอบงำ ซึ่งเป็นบั๊กที่เคยเกิดขึ้นจริง (ดู PROBLEMS.md ปัญหา 05.1)

---

## เพิ่มความรู้ใหม่เข้าฐานข้อมูล

เปิด `data-basic.js` หรือ `data-advanced.js` แล้วเพิ่มบล็อกตามรูปแบบด้านบน

**ข้อควรระวัง:** ใส่ `alt` อย่างน้อย 2 ข้อ เพราะระบบแบ่งลำดับคู่ไปเข้าดัชนี
และลำดับคี่กันไว้เป็นชุดทดสอบ ถ้าใส่แค่ข้อเดียวจะไม่มีคำถามทดสอบสำหรับเอกสารนั้น

ถ้าเพิ่มศัพท์เฉพาะใหม่ที่มีทั้งคำไทยและอังกฤษ ควรเพิ่มกลุ่มคำพ้องใน `config.js → TRADING_SYNONYMS` ด้วย

---

## ปรับพารามิเตอร์

แก้ได้ 2 ทาง

1. **ผ่านหน้าเว็บ** แท็บ *ตั้งค่า* — เปลี่ยนแล้วมีผลทันที และบันทึกใน localStorage
2. **แก้ `config.js` โดยตรง** — เปลี่ยนค่าตั้งต้นของระบบ

ค่าที่กระทบดัชนี (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `NGRAM_*`, `NORMALIZE_TEXT`, `DEDUPE_DOCS`)
ต้องกด **สร้างดัชนีใหม่** จึงจะมีผล

---

## เชื่อมต่อ LLM จริง (ทางเลือก)

1. ไปที่แท็บ *ตั้งค่า* กลุ่มที่ 5
2. เปิดสวิตช์ `USE_LLM`
3. เลือกผู้ให้บริการ (`gemini` หรือ `openai`) ระบุชื่อโมเดล และใส่ API Key ของตัวเอง

API Key เก็บใน localStorage ของเบราว์เซอร์เท่านั้น ไม่ถูกส่งไปที่อื่นนอกจากผู้ให้บริการที่เลือก
ถ้าเรียก API ไม่สำเร็จ ระบบจะใช้คำตอบจากฐานความรู้แทนโดยอัตโนมัติ

Prompt ที่ส่งไปกำหนดกฎชัดเจนว่าให้ใช้เฉพาะข้อมูลจากบริบท ห้ามเดา และห้ามให้คำแนะนำการลงทุน
ดูได้ที่ `rag-generate.js → buildPrompt()`
