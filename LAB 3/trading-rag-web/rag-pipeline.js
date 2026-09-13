/* =============================================================
 *  rag-pipeline.js — ต่อทุกขั้นตอนเข้าด้วยกันเป็น RAG Pipeline เดียว
 *
 *  Ingestion -> Chunking -> Indexing        (ทำครั้งเดียวตอนเปิดเว็บ)
 *  Query -> Retrieval -> Rerank -> Generate (ทำทุกครั้งที่ผู้ใช้ถาม)
 *
 *  ทุกขั้นตอนบันทึก trace ไว้ เพื่อให้หน้า "ตรวจสอบ Pipeline" แสดงได้ว่า
 *  ระบบคิดอะไรในแต่ละชั้น ซึ่งเป็นเครื่องมือหลักในการ "ตรวจสอบปัญหา"
 * ============================================================= */

window.RagPipeline = (function () {

  var built = null;

  /* ---------- ขั้นเตรียมข้อมูล (ทำครั้งเดียว / ทำใหม่เมื่อเปลี่ยน config) ---------- */
  function buildIndex() {
    var t0 = performance.now();

    var raw = window.TRADING_KB || [];
    var clean = window.RagNormalize.dedupe(raw);
    var t1 = performance.now();

    var chunks = window.RagChunk.buildChunks(clean.docs);
    var t2 = performance.now();

    var idxStats = window.RagIndex.build(chunks);
    var t3 = performance.now();

    built = {
      rawDocs: raw.length,
      docs: clean.docs.length,
      removed: clean.removed,
      issues: clean.issues,
      chunkStats: window.RagChunk.stats(chunks),
      indexStats: idxStats,
      timing: {
        clean: +(t1 - t0).toFixed(1),
        chunk: +(t2 - t1).toFixed(1),
        index: +(t3 - t2).toFixed(1),
        total: +(t3 - t0).toFixed(1)
      }
    };
    return built;
  }

  function getBuild() { return built; }

  /* ---------- ขั้นตอบคำถาม ---------- */
  function ask(rawQuery) {
    if (!window.RagIndex.isBuilt()) buildIndex();

    var trace = { query: rawQuery, stages: [] };
    var t0 = performance.now();

    // Stage 4 : Query Transformation
    var q = window.RagQuery.transform(rawQuery);
    q.raw = rawQuery;
    var t1 = performance.now();
    trace.stages.push({
      no: 1,
      name: "Query Transformation",
      icon: "search",
      detail: q.trace.steps,
      ms: +(t1 - t0).toFixed(1)
    });

    // Stage 5 : Retrieval
    var ret = window.RagRetrieve.retrieve(q);
    var t2 = performance.now();
    trace.stages.push({
      no: 2,
      name: "Retrieval (" + window.RAG_CONFIG.RETRIEVAL_MODE + ")",
      icon: "database",
      detail: ret.trace.lists.map(function (l) {
        return { name: l.name, value: l.size + " ชิ้น" };
      }).concat([
        { name: "ถูกกรองด้วย Metadata", value: ret.trace.filteredOut + " ชิ้น" },
        { name: "ส่งต่อไป Rerank", value: ret.trace.returned + " ชิ้น" }
      ]),
      ms: +(t2 - t1).toFixed(1)
    });

    // Stage 6 : Re-ranking
    var ranked = window.RagRerank.rerank(ret.results, q);
    var t3 = performance.now();
    var movedUp = ranked.filter(function (r) { return (r.moved || 0) > 0; }).length;
    trace.stages.push({
      no: 3,
      name: "Re-ranking",
      icon: "sort",
      detail: [
        { name: "สถานะ", value: window.RAG_CONFIG.USE_RERANK ? "เปิดใช้งาน" : "ปิดอยู่" },
        { name: "เอกสารที่ถูกเลื่อนอันดับขึ้น", value: movedUp + " ชิ้น" },
        { name: "คะแนนสูงสุดหลังจัดอันดับ", value: ranked.length ? ranked[0].score.toFixed(3) : "-" }
      ],
      ms: +(t3 - t2).toFixed(1)
    });

    // Stage 7-8 : Guardrail + Generation
    var gen = window.RagGenerate.generate(rawQuery, ranked);
    var t4 = performance.now();
    trace.stages.push({
      no: 4,
      name: "Guardrail + Generation",
      icon: "shield",
      detail: [
        { name: "เกณฑ์หลักฐานขั้นต่ำ", value: String(window.RAG_CONFIG.GROUNDING_THRESHOLD) },
        { name: "คะแนนหลักฐานที่ได้", value: gen.info.topScore ? gen.info.topScore.toFixed(3) : "0" },
        { name: "ผลการตรวจ", value: gen.info.refused ? ("ปฏิเสธการตอบ — " + gen.info.reason) : "ผ่าน ตอบจากบริบท" },
        { name: "Faithfulness", value: gen.info.faithfulness ? (gen.info.faithfulness * 100).toFixed(1) + "%" : "-" },
        { name: "แหล่งอ้างอิง", value: gen.info.citations.length ? gen.info.citations.join(", ") : "-" }
      ],
      ms: +(t4 - t3).toFixed(1)
    });

    trace.totalMs = +(t4 - t0).toFixed(1);

    return {
      query: rawQuery,
      queryObj: q,
      results: ranked,
      answer: gen.text,
      info: gen.info,
      trace: trace
    };
  }

  /* ---------- โหมดใช้ LLM จริง (ทางเลือก) ---------- */
  function askWithLLM(rawQuery) {
    var base = ask(rawQuery);
    if (base.info.refused) return Promise.resolve(base);

    var contexts = base.results.slice(0, window.RAG_CONFIG.TOP_K_CONTEXT);
    return window.RagGenerate.callLLM(rawQuery, contexts)
      .then(function (text) {
        base.answer = text;
        base.info.faithfulness = window.RagGenerate.faithfulness(text, contexts);
        base.info.llm = window.RAG_CONFIG.LLM_PROVIDER + " / " + window.RAG_CONFIG.LLM_MODEL;
        base.trace.stages.push({
          no: 5,
          name: "LLM Generation",
          icon: "sparkles",
          detail: [
            { name: "ผู้ให้บริการ", value: base.info.llm },
            { name: "Faithfulness หลังใช้ LLM", value: (base.info.faithfulness * 100).toFixed(1) + "%" }
          ],
          ms: 0
        });
        return base;
      })
      .catch(function (err) {
        base.answer += "\n\n(เรียก LLM ไม่สำเร็จ: " + err.message + " — ระบบใช้คำตอบจากฐานความรู้แทน)";
        return base;
      });
  }

  return { buildIndex: buildIndex, getBuild: getBuild, ask: ask, askWithLLM: askWithLLM };
})();
