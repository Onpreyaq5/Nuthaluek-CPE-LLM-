/* =============================================================
 *  rag-index.js — Stage 3 : Indexing (Vector Index + BM25 Index)
 *
 *  สร้างดัชนี 2 ชุดจาก chunk ชุดเดียวกัน เพื่อใช้ทำ Hybrid Retrieval
 *   1) Vector Index (TF-IDF + Cosine)  -> จับ "ความคล้ายเชิงความหมายโดยรวม"
 *   2) BM25 Index                      -> จับ "คำเฉพาะที่ตรงตัว" เช่น RSI, MACD, 61.8
 *
 *  หมายเหตุเชิงวิชาการ (สำคัญ / เขียนไว้ใน PROBLEMS.md ปัญหา 03 ด้วย)
 *  ระบบนี้ทำงานบนเบราว์เซอร์ล้วน ไม่เรียก Embedding Model จริง
 *  จึงใช้ TF-IDF Vector Space Model ทำหน้าที่แทน Dense Embedding
 *  ข้อดีคือรันได้ทุกที่ไม่ต้องมี API Key ข้อจำกัดคือไม่เข้าใจความหมายที่คำไม่ซ้ำกันเลย
 *  ระบบจึงชดเชยด้วยชั้นขยายคำพ้อง (rag-query.js) แทน
 * ============================================================= */

window.RagIndex = (function () {

  var state = {
    chunks: [],
    vectors: [],     // [{ chunkId, vec: {token: weight}, norm }]
    idf: {},         // token -> ค่า idf
    df: {},          // token -> จำนวนเอกสารที่มี token นี้
    bm25: null,      // ดัชนีสำหรับ BM25
    built: false
  };

  /* ---------- สร้างดัชนีทั้งหมด ---------- */
  function build(chunks) {
    var N = chunks.length;
    var df = {};
    var docTokens = [];
    var docLens = [];
    var totalLen = 0;

    // รอบที่ 1 : ตัดคำและนับ document frequency
    for (var i = 0; i < N; i++) {
      var toks = window.RagNormalize.tokenize(chunks[i].text);
      var tf = window.RagNormalize.termFreq(toks);
      docTokens.push(tf);
      docLens.push(toks.length);
      totalLen += toks.length;

      for (var t in tf) {
        if (Object.prototype.hasOwnProperty.call(tf, t)) df[t] = (df[t] || 0) + 1;
      }
    }

    // รอบที่ 2 : คำนวณ IDF
    var idf = {};
    for (var term in df) {
      if (!Object.prototype.hasOwnProperty.call(df, term)) continue;
      // smoothed idf กัน log(0) และกันค่าติดลบ
      idf[term] = Math.log(1 + (N - df[term] + 0.5) / (df[term] + 0.5));
    }

    // รอบที่ 3 : สร้างเวกเตอร์ TF-IDF และค่าความยาวเวกเตอร์ (norm)
    var vectors = [];
    for (var d = 0; d < N; d++) {
      var vec = {};
      var sumSq = 0;
      var tfd = docTokens[d];
      for (var tk in tfd) {
        if (!Object.prototype.hasOwnProperty.call(tfd, tk)) continue;
        var w = (1 + Math.log(tfd[tk])) * (window.RAG_CONFIG.USE_IDF ? (idf[tk] || 0) : 1);
        if (w > 0) { vec[tk] = w; sumSq += w * w; }
      }
      vectors.push({
        chunkId: chunks[d].chunkId,
        idx: d,
        vec: vec,
        norm: Math.sqrt(sumSq) || 1
      });
    }

    state.chunks = chunks;
    state.vectors = vectors;
    state.idf = idf;
    state.df = df;
    state.bm25 = {
      docTokens: docTokens,
      docLens: docLens,
      avgLen: totalLen / (N || 1),
      N: N
    };
    state.built = true;

    return {
      chunks: N,
      vocabulary: Object.keys(df).length,
      avgTokensPerChunk: Math.round(totalLen / (N || 1))
    };
  }

  /* ---------- ค้นแบบ Vector (Cosine Similarity) ---------- */
  function denseSearch(queryTokens, topK) {
    var qtf = window.RagNormalize.termFreq(queryTokens);
    var qvec = {};
    var qSumSq = 0;

    for (var t in qtf) {
      if (!Object.prototype.hasOwnProperty.call(qtf, t)) continue;
      var w = (1 + Math.log(qtf[t])) * (window.RAG_CONFIG.USE_IDF ? (state.idf[t] || 0) : 1);
      if (w > 0) { qvec[t] = w; qSumSq += w * w; }
    }
    var qNorm = Math.sqrt(qSumSq) || 1;

    var scored = [];
    for (var i = 0; i < state.vectors.length; i++) {
      var v = state.vectors[i];
      var dot = 0;
      // วนเฉพาะ token ของ query (สั้นกว่ามาก) เพื่อความเร็ว
      for (var qt in qvec) {
        if (v.vec[qt]) dot += qvec[qt] * v.vec[qt];
      }
      if (dot > 0) {
        scored.push({ idx: i, chunkId: v.chunkId, score: dot / (qNorm * v.norm) });
      }
    }
    scored.sort(function (a, b) { return b.score - a.score; });
    return scored.slice(0, topK || 20);
  }

  /* ---------- ค้นแบบ BM25 ---------- */
  function bm25Search(queryTokens, topK) {
    var cfg = window.RAG_CONFIG;
    var k1 = cfg.BM25_K1, b = cfg.BM25_B;
    var bm = state.bm25;
    if (!bm) return [];

    // ตัด token ซ้ำใน query ออก เพื่อไม่ให้คำเดียวถูกนับหลายรอบ
    var uniq = {};
    for (var i = 0; i < queryTokens.length; i++) uniq[queryTokens[i]] = true;
    var terms = Object.keys(uniq);

    var scored = [];
    for (var d = 0; d < bm.N; d++) {
      var score = 0;
      var dl = bm.docLens[d] || 1;
      var tfd = bm.docTokens[d];

      for (var j = 0; j < terms.length; j++) {
        var term = terms[j];
        var f = tfd[term];
        if (!f) continue;
        var idf = state.idf[term] || 0;
        score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * (dl / bm.avgLen)));
      }
      if (score > 0) {
        scored.push({ idx: d, chunkId: state.chunks[d].chunkId, score: score });
      }
    }
    scored.sort(function (a, b2) { return b2.score - a.score; });
    return scored.slice(0, topK || 20);
  }

  /* ---------- ค่า IDF ของ token หนึ่งตัว ----------
   * token ที่ "ไม่เคยปรากฏในคลังเลย" ถือว่าหายากที่สุด จึงได้ค่าสูงสุด
   * คุณสมบัตินี้สำคัญมาก เพราะทำให้คำถามนอกขอบเขต (ที่เต็มไปด้วยคำซึ่งไม่มีในคลัง)
   * ได้คะแนนหลักฐานต่ำโดยอัตโนมัติ -> เป็นฐานของการกัน Hallucination
   */
  function idfOf(token) {
    if (state.idf[token] !== undefined) return state.idf[token];
    var N = state.bm25 ? state.bm25.N : 1;
    return Math.log(1 + (N + 0.5) / 0.5);   // ค่าเทียบเท่า df = 0
  }

  function getChunk(idx) { return state.chunks[idx]; }
  function getChunks() { return state.chunks; }
  function isBuilt() { return state.built; }
  function getStats() {
    return {
      chunks: state.chunks.length,
      vocabulary: Object.keys(state.df).length,
      avgLen: state.bm25 ? Math.round(state.bm25.avgLen) : 0
    };
  }

  return {
    build: build,
    denseSearch: denseSearch,
    bm25Search: bm25Search,
    idfOf: idfOf,
    getChunk: getChunk,
    getChunks: getChunks,
    isBuilt: isBuilt,
    getStats: getStats
  };
})();
