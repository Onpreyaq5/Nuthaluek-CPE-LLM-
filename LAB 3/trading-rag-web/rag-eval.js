/* =============================================================
 *  rag-eval.js — Stage 9 : Evaluation
 *
 *  แก้ปัญหา 09 (ปรับระบบไปเรื่อย ๆ โดยไม่รู้ว่าดีขึ้นจริงหรือไม่)
 *
 *  Golden Set สร้างอัตโนมัติจากฐานความรู้
 *  โดยใช้ "คำถามสำรอง (alt)" ของแต่ละเอกสารเป็นคำถามทดสอบ
 *  และถือว่าเอกสารต้นทางคือคำตอบที่ถูกต้อง (Relevant Document)
 *  ข้อดีคือคำถามสำรองเขียนด้วยสำนวนที่ต่างจากคำถามหลัก จึงวัด Retrieval ได้จริง
 *  ไม่ใช่การทดสอบด้วยข้อความที่ตรงกันทุกตัวอักษร
 *
 *  ตัวชี้วัด
 *   Hit@k       : เอกสารที่ถูกต้องติดอันดับ k แรกหรือไม่ (0 หรือ 1) เฉลี่ยทุกคำถาม
 *   MRR         : ค่าเฉลี่ยของ 1/อันดับแรกที่เจอเอกสารถูกต้อง
 *   nDCG@k      : ให้น้ำหนักอันดับต้น ๆ มากกว่า ยิ่งเจอเร็วยิ่งได้คะแนนสูง
 *   Precision@k : สัดส่วนเอกสารที่ถูกต้องใน k อันดับแรก
 * ============================================================= */

window.RagEval = (function () {

  /* ---------- สร้าง Golden Set ----------
   * ใช้เฉพาะคำถามสำรอง "ชุดที่กันไว้ทดสอบ" (heldOut) เท่านั้น
   * ชุดนี้ไม่เคยถูกใส่ลงในดัชนีและไม่เคยถูกใช้ตอน Re-ranking
   * ตัวเลขที่วัดได้จึงสะท้อนความสามารถในการค้นหาจริง ไม่ใช่การจับคู่ข้อความที่รู้คำตอบอยู่แล้ว
   */
  function buildGoldenSet() {
    var kb = window.TRADING_KB || [];
    var set = [];
    for (var i = 0; i < kb.length; i++) {
      var d = kb[i];
      var held = window.RagNormalize.splitAlt(d.alt).heldOut;
      for (var j = 0; j < held.length; j++) {
        set.push({ query: held[j], relevantDocId: d.id, cat: d.cat, level: d.level });
      }
    }
    return set;
  }

  /* ---------- ค้นหาอันดับของเอกสารที่ถูกต้อง ---------- */
  function rankOfRelevant(results, docId) {
    var seen = {};
    var rank = 0;
    for (var i = 0; i < results.length; i++) {
      var id = results[i].chunk.docId;
      if (seen[id]) continue;   // นับระดับเอกสาร ไม่ใช่ระดับ chunk
      seen[id] = true;
      rank++;
      if (id === docId) return rank;
    }
    return -1;
  }

  function dcgAt(rank, k) {
    if (rank < 1 || rank > k) return 0;
    return 1 / (Math.log2(rank + 1));
  }

  /* ---------- รันประเมินผลหนึ่งชุดค่า config ---------- */
  function run(goldenSet, kValues) {
    kValues = kValues || window.RAG_CONFIG.EVAL_K_VALUES;
    var maxK = Math.max.apply(null, kValues);

    var hits = {}, ndcg = {}, precision = {};
    for (var a = 0; a < kValues.length; a++) {
      hits[kValues[a]] = 0; ndcg[kValues[a]] = 0; precision[kValues[a]] = 0;
    }
    var mrrSum = 0;
    var found = 0;
    var failures = [];

    for (var i = 0; i < goldenSet.length; i++) {
      var item = goldenSet[i];
      var res = window.RagPipeline.ask(item.query);
      var rank = rankOfRelevant(res.results, item.relevantDocId);

      if (rank > 0) {
        found++;
        mrrSum += 1 / rank;
      } else {
        failures.push({
          query: item.query,
          expected: item.relevantDocId,
          got: res.results.length ? res.results[0].chunk.docId : "(ไม่พบอะไรเลย)"
        });
      }

      for (var b = 0; b < kValues.length; b++) {
        var k = kValues[b];
        if (rank > 0 && rank <= k) {
          hits[k] += 1;
          ndcg[k] += dcgAt(rank, k);   // IDCG = 1 เพราะมีเอกสารถูกต้อง 1 ชิ้น
          precision[k] += 1 / k;
        }
      }
    }

    var n = goldenSet.length || 1;
    var out = { total: goldenSet.length, found: found, mrr: mrrSum / n, k: {}, failures: failures };
    for (var c = 0; c < kValues.length; c++) {
      var kk = kValues[c];
      out.k[kk] = {
        hit: hits[kk] / n,
        ndcg: ndcg[kk] / n,
        precision: precision[kk] / n
      };
    }
    return out;
  }

  /* ---------- Ablation Study : ปิด/เปิดแต่ละเทคนิคแล้วเทียบผล ---------- *
   * นี่คือหลักฐานเชิงตัวเลขว่า "การแก้ปัญหาแต่ละข้อช่วยจริงหรือไม่"
   */
  var ABLATIONS = [
    {
      name: "BM25 อย่างเดียว",
      note: "ค้นด้วยคำตรงตัว ไม่มีการรวมผล",
      cfg: { RETRIEVAL_MODE: "bm25", USE_RERANK: false, QUERY_SYNONYM_EXPANSION: false, QUERY_MULTI: false }
    },
    {
      name: "Vector อย่างเดียว",
      note: "TF-IDF Cosine ไม่มีการรวมผล",
      cfg: { RETRIEVAL_MODE: "dense", USE_RERANK: false, QUERY_SYNONYM_EXPANSION: false, QUERY_MULTI: false }
    },
    {
      name: "Hybrid (RRF)",
      note: "รวมอันดับ BM25 + Vector",
      cfg: { RETRIEVAL_MODE: "hybrid", USE_RERANK: false, QUERY_SYNONYM_EXPANSION: false, QUERY_MULTI: false }
    },
    {
      name: "Hybrid + ขยายคำพ้อง",
      note: "เพิ่มการเชื่อมคำไทย-อังกฤษ",
      cfg: { RETRIEVAL_MODE: "hybrid", USE_RERANK: false, QUERY_SYNONYM_EXPANSION: true, QUERY_MULTI: true }
    },
    {
      name: "Hybrid + คำพ้อง + Rerank",
      note: "ระบบเต็มรูปแบบที่ใช้งานจริง",
      cfg: { RETRIEVAL_MODE: "hybrid", USE_RERANK: true, QUERY_SYNONYM_EXPANSION: true, QUERY_MULTI: true }
    }
  ];

  function runAblation(goldenSet, kValues, onProgress) {
    var backup = JSON.parse(JSON.stringify(window.RAG_CONFIG));
    var rows = [];

    for (var i = 0; i < ABLATIONS.length; i++) {
      var ab = ABLATIONS[i];
      for (var key in ab.cfg) {
        if (Object.prototype.hasOwnProperty.call(ab.cfg, key)) window.RAG_CONFIG[key] = ab.cfg[key];
      }
      var r = run(goldenSet, kValues);
      rows.push({ name: ab.name, note: ab.note, result: r });
      if (onProgress) onProgress(i + 1, ABLATIONS.length, ab.name);
    }

    // คืนค่า config เดิม
    for (var k2 in backup) {
      if (Object.prototype.hasOwnProperty.call(backup, k2)) window.RAG_CONFIG[k2] = backup[k2];
    }
    return rows;
  }

  /* ---------- ประเมินผลกระทบของขนาด chunk (ต้องสร้างดัชนีใหม่) ---------- */
  function runChunkStudy(goldenSet, sizes) {
    var backup = JSON.parse(JSON.stringify(window.RAG_CONFIG));
    var rows = [];

    for (var i = 0; i < sizes.length; i++) {
      window.RAG_CONFIG.CHUNK_SIZE = sizes[i].size;
      window.RAG_CONFIG.CHUNK_OVERLAP = sizes[i].overlap;
      var b = window.RagPipeline.buildIndex();
      var r = run(goldenSet, [1, 3, 5]);
      rows.push({
        size: sizes[i].size,
        overlap: sizes[i].overlap,
        chunks: b.chunkStats.count,
        avgLen: b.chunkStats.avg,
        result: r
      });
    }

    for (var k in backup) {
      if (Object.prototype.hasOwnProperty.call(backup, k)) window.RAG_CONFIG[k] = backup[k];
    }
    window.RagPipeline.buildIndex();   // สร้างดัชนีกลับเป็นค่าปัจจุบัน
    return rows;
  }

  return {
    buildGoldenSet: buildGoldenSet,
    run: run,
    runAblation: runAblation,
    runChunkStudy: runChunkStudy,
    ABLATIONS: ABLATIONS
  };
})();
