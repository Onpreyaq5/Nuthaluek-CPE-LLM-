/* =============================================================
 *  rag-retrieve.js — Stage 5 : Retrieval
 *
 *  แก้ปัญหา 05 (ค้นด้วยวิธีเดียวแพ้บางประเภทคำถาม)
 *   - Dense อย่างเดียว : ดีกับคำถามเชิงความหมาย แต่พลาดศัพท์เฉพาะที่ต้องตรงตัว
 *   - BM25 อย่างเดียว  : ดีกับศัพท์เฉพาะ แต่พลาดเมื่อผู้ใช้ใช้คำอื่นที่ความหมายเดียวกัน
 *   -> ทางแก้คือ Hybrid + Reciprocal Rank Fusion (RRF) รวมอันดับจากทั้งสองวิธี
 *
 *  และแก้ปัญหา 07 (Metadata Filtering) ด้วยการกรองตามหมวด/ระดับก่อนให้คะแนน
 * ============================================================= */

window.RagRetrieve = (function () {

  /* ---------- Reciprocal Rank Fusion (แบบถ่วงน้ำหนักได้) ---------- *
   * RRF ใช้ "อันดับ" ไม่ใช่ "คะแนนดิบ" จึงรวมผลจากคนละสเกลได้โดยไม่ต้อง normalize
   * สูตร : score(d) = ผลรวมของ w_i / (k + rank_i(d)) จากทุกรายการผลลัพธ์
   *
   * เหตุผลที่ต้องมีน้ำหนัก : รายการที่มาจาก "คำถามเดิม" ควรมีเสียงดังกว่า
   * รายการที่มาจาก "คำถามที่ขยายคำพ้องแล้ว" เพราะคำที่เติมเข้าไปเป็นการเดา
   * ถ้าให้น้ำหนักเท่ากัน คำถามเดิมจะถูกกลบจนผลแย่ลงกว่าไม่ขยายเสียอีก
   */
  function rrfFuse(lists, k) {
    var table = {};
    for (var l = 0; l < lists.length; l++) {
      var list = lists[l];
      var w = (list.weight == null) ? 1 : list.weight;
      for (var r = 0; r < list.length; r++) {
        var item = list[r];
        if (!table[item.idx]) {
          table[item.idx] = { idx: item.idx, chunkId: item.chunkId, score: 0, sources: {} };
        }
        table[item.idx].score += w / (k + (r + 1));
        table[item.idx].sources[list.name || ("list" + l)] = r + 1;
      }
    }
    var out = [];
    for (var key in table) {
      if (Object.prototype.hasOwnProperty.call(table, key)) out.push(table[key]);
    }
    out.sort(function (a, b) { return b.score - a.score; });
    return out;
  }

  /* ---------- กรองตาม Metadata ---------- */
  function passFilter(chunk) {
    var cfg = window.RAG_CONFIG;
    if (!cfg.USE_METADATA_FILTER) return true;
    if (cfg.FILTER_LEVEL !== "ทั้งหมด" && chunk.level !== cfg.FILTER_LEVEL) return false;
    if (cfg.FILTER_CATEGORY !== "ทั้งหมด" && chunk.cat !== cfg.FILTER_CATEGORY) return false;
    return true;
  }

  /* ---------- ฟังก์ชันหลัก ---------- */
  function retrieve(queryObj) {
    var cfg = window.RAG_CONFIG;
    var topK = cfg.TOP_K_FIRST;
    var trace = { mode: cfg.RETRIEVAL_MODE, lists: [] };

    // แยก token เป็น 3 ชุดที่มาจากคนละแหล่ง และมีความน่าเชื่อถือต่างกัน
    //  baseTokens : คำถามเดิมของผู้ใช้ล้วน ๆ            -> น้ำหนักเต็ม
    //  synTokens  : "คำพ้องที่เติมเข้าไปเท่านั้น"        -> น้ำหนักเกือบเต็ม (มาจากพจนานุกรมที่คัดเอง)
    //  varTokens  : รูปแบบคำถามที่ระบบสร้างเอง          -> น้ำหนักต่ำ (เป็นการเดา)
    //
    // จุดที่เคยพลาด : เดิมเอา "คำถามเดิม + คำพ้อง" มารวมเป็นรายการเดียว
    // อันดับของรายการนั้นจึงถูกคำถามเดิมครอบงำ คำพ้องแทบไม่มีผล
    // กรณีที่เห็นชัดคือถามว่า "ดัชนีกำลังสัมพัทธ์" ซึ่งไม่มีคำนี้อยู่ในเอกสารใดเลย
    // อันดับจากคำถามเดิมจึงเป็นเพียงสัญญาณรบกวน และกลบเอกสาร RSI ที่ถูกต้องจนมิด
    var baseTokens = window.RagNormalize.tokenize(queryObj.base || queryObj.main);

    var synText = (queryObj.synonyms || []).join(" ");
    var synTokens = synText ? window.RagNormalize.tokenize(synText) : [];

    var varTokens = [];
    for (var v = 0; v < queryObj.variants.length; v++) {
      if (queryObj.variants[v] === queryObj.main) continue;
      varTokens = varTokens.concat(window.RagNormalize.tokenize(queryObj.variants[v]));
    }

    var W_BASE = 1.0, W_SYN = 0.9, W_VAR = 0.45;
    var lists = [];

    function mk(arr, name, weight) { arr.name = name; arr.weight = weight; return arr; }
    function addList(fn, tokens, name, weight) {
      if (!tokens.length) return;
      lists.push(mk(fn(tokens, topK * 2), name, weight));
    }

    var dense = window.RagIndex.denseSearch, bm = window.RagIndex.bm25Search;
    var useDense = cfg.RETRIEVAL_MODE !== "bm25";
    var useBm = cfg.RETRIEVAL_MODE !== "dense";

    if (useDense) addList(dense, baseTokens, "dense (คำถามเดิม)", W_BASE);
    if (useBm) addList(bm, baseTokens, "bm25 (คำถามเดิม)", W_BASE);
    if (useDense) addList(dense, synTokens, "dense (คำพ้อง)", W_SYN);
    if (useBm) addList(bm, synTokens, "bm25 (คำพ้อง)", W_SYN);
    if (useDense) addList(dense, varTokens, "dense (multi-query)", W_VAR);

    var fused = rrfFuse(lists, cfg.RRF_K);
    for (var li = 0; li < lists.length; li++) {
      trace.lists.push({ name: lists[li].name + " (น้ำหนัก " + lists[li].weight + ")", size: lists[li].length });
    }
    trace.lists.push({ name: "RRF Fusion", size: fused.length });

    // แนบตัว chunk จริง + กรอง metadata
    var results = [];
    var filteredOut = 0;
    for (var i = 0; i < fused.length; i++) {
      var chunk = window.RagIndex.getChunk(fused[i].idx);
      if (!chunk) continue;
      if (!passFilter(chunk)) { filteredOut++; continue; }
      results.push({
        chunk: chunk,
        firstStageScore: fused[i].score,
        sources: fused[i].sources,
        rank: results.length + 1
      });
      if (results.length >= topK) break;
    }

    trace.filteredOut = filteredOut;
    trace.returned = results.length;
    return { results: results, trace: trace };
  }

  return { retrieve: retrieve, rrfFuse: rrfFuse, passFilter: passFilter };
})();
