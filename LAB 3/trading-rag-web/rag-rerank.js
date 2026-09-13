/* =============================================================
 *  rag-rerank.js — Stage 6 : Re-ranking
 *
 *  แก้ปัญหา 06 (First-stage Retrieval จัดอันดับเอกสารที่ถูกต้องไว้ต่ำเกินไป)
 *
 *  หลักการ : first-stage เน้น "เร็ว" จึงให้คะแนนหยาบ ๆ จากความถี่คำ
 *  ส่วน rerank มองผู้สมัครไม่กี่ชิ้น จึงใช้สัญญาณละเอียดกว่าได้
 *   - ความครอบคลุมคำในคำถาม (Coverage)
 *   - ตรงกับ "คำถามหลัก/คำถามสำรอง" ของเอกสารหรือไม่ (Title match)
 *   - ตรงกับ tags หรือไม่
 *   - มีศัพท์เฉพาะตรงตัวหรือไม่ เช่น rsi, macd, vwap, 61.8
 * ============================================================= */

window.RagRerank = (function () {

  function uniq(arr) {
    var seen = {}, out = [];
    for (var i = 0; i < arr.length; i++) {
      if (!seen[arr[i]]) { seen[arr[i]] = true; out.push(arr[i]); }
    }
    return out;
  }

  /* ---------- ความครอบคลุมคำถาม ถ่วงน้ำหนักด้วย IDF (0..1) ----------
   * เหตุผลที่ต้องถ่วงน้ำหนัก : ภาษาไทยตัดด้วย n-gram จะได้ชิ้นส่วนทั่วไปจำนวนมาก
   * เช่น "ที่" "การ" "ราคา" ซึ่งปรากฏแทบทุกเอกสาร ถ้านับทุก token เท่ากัน
   * คำถามที่ไม่เกี่ยวข้องเลยก็ยังได้คะแนนสูงจนหลอกด่าน Grounding ได้
   * การถ่วงด้วย IDF ทำให้เฉพาะ "คำที่มีความหมายเฉพาะ" เท่านั้นที่มีน้ำหนักจริง
   */
  function coverage(qTokens, chunkTokenSet) {
    if (!qTokens.length) return 0;
    var total = 0, hit = 0;
    for (var i = 0; i < qTokens.length; i++) {
      var w = window.RagIndex.idfOf(qTokens[i]);
      total += w;
      if (chunkTokenSet[qTokens[i]]) hit += w;
    }
    return total ? hit / total : 0;
  }

  /* ความตรงกับคำถามหลัก/คำถามสำรองของเอกสาร */
  function titleMatch(qNorm, chunk) {
    var titles = [chunk.q].concat(chunk.alt || []);
    var best = 0;
    for (var i = 0; i < titles.length; i++) {
      var t = window.RagNormalize.normalizeText(titles[i]);
      if (!t) continue;
      if (t === qNorm) return 1;                       // ตรงเป๊ะ
      if (t.indexOf(qNorm) !== -1 && qNorm.length >= 3) best = Math.max(best, 0.85);
      if (qNorm.indexOf(t) !== -1 && t.length >= 4) best = Math.max(best, 0.75);
    }
    return best;
  }

  function tagMatch(qNorm, chunk) {
    var tags = chunk.tags || [];
    for (var i = 0; i < tags.length; i++) {
      var t = window.RagNormalize.normalizeText(tags[i]);
      // ต้องยาวอย่างน้อย 3 ตัวอักษร กัน tag สั้นอย่าง "ma" ไปตรงกับคำอื่นโดยบังเอิญ
      if (t && t.length >= 3 && qNorm.indexOf(t) !== -1) return 1;
    }
    return 0;
  }

  /* ศัพท์เฉพาะที่ต้องตรงตัว (ตัวอักษรละติน/ตัวเลข) เช่น rsi macd 61.8 */
  function exactTermMatch(qNorm, chunk) {
    var terms = qNorm.match(/[a-z0-9]+(?:\.[0-9]+)?/g) || [];
    if (!terms.length) return 0;
    var text = window.RagNormalize.normalizeText(chunk.text);
    var hit = 0;
    for (var i = 0; i < terms.length; i++) {
      if (terms[i].length < 2) continue;
      if (text.indexOf(terms[i]) !== -1) hit++;
    }
    return terms.length ? hit / terms.length : 0;
  }

  /* ---------- ฟังก์ชันหลัก ----------
   * คำนวณ 2 ค่าที่ทำหน้าที่ต่างกัน และต้องไม่ปนกัน
   *  1) grounding = "มีหลักฐานรองรับแค่ไหน"  -> ใช้ตัดสินว่าจะตอบหรือปฏิเสธ
   *     คำนวณเสมอ ไม่ว่าจะเปิดหรือปิด rerank ด่านกัน Hallucination จึงไม่หายไป
   *     เมื่อผู้ใช้ปิด rerank
   *  2) score     = "ควรอยู่อันดับไหน"       -> ใช้เรียงลำดับผลลัพธ์
   */
  function rerank(candidates, queryObj) {
    var cfg = window.RAG_CONFIG;

    // เก็บอันดับเดิมไว้ เพื่อเทียบ "ก่อน/หลัง rerank" ในหน้า Problem Lab
    for (var i = 0; i < candidates.length; i++) candidates[i].rankBefore = i + 1;

    // ใช้คำถาม 2 รูปแบบให้ถูกหน้าที่
    //  qBase = คำถามดิบของผู้ใช้    -> ใช้เทียบกับ "คำถามหลัก" ของเอกสาร (title match)
    //                                  เพราะต้องการวัดว่าผู้ใช้ถามตรงกับหัวข้อนั้นจริงไหม
    //  qExp  = คำถามที่ขยายคำพ้องแล้ว -> ใช้วัดความครอบคลุมและศัพท์เฉพาะ
    //                                  ถ้าใช้แต่คำถามดิบ คำพ้องที่เติมไปจะช่วยแค่ตอนค้น
    //                                  แต่ไม่ช่วยตอนจัดอันดับ เอกสารที่ถูกจึงยังถูกกดอยู่ล่าง
    var qBase = window.RagNormalize.normalizeText(queryObj.base || queryObj.raw || queryObj.main);
    var qExp = window.RagNormalize.normalizeText(queryObj.main);
    var qTokens = uniq(window.RagNormalize.tokenize(qExp));

    var maxFirst = 0;
    for (var a = 0; a < candidates.length; a++) {
      maxFirst = Math.max(maxFirst, candidates[a].firstStageScore || 0);
    }

    for (var c = 0; c < candidates.length; c++) {
      var ch = candidates[c].chunk;

      // สร้างชุด token ของ chunk (ทำครั้งเดียวแล้ว cache ไว้ที่ตัว chunk)
      if (!ch._tokenSet) {
        var toks = window.RagNormalize.tokenize(ch.text);
        var set = {};
        for (var t = 0; t < toks.length; t++) set[toks[t]] = true;
        ch._tokenSet = set;
      }

      var cov = coverage(qTokens, ch._tokenSet);
      var firstNorm = maxFirst ? (candidates[c].firstStageScore / maxFirst) : 0;
      var title = titleMatch(qBase, ch);
      var tag = tagMatch(qExp, ch);
      var exact = exactTermMatch(qExp, ch);

      // --- คะแนนหลักฐาน : ขึ้นกับสิ่งที่ "ตรงกันจริง" เท่านั้น ---
      // ไม่มีคำสำคัญตรงกันเลย = ได้ศูนย์ ต่อให้เป็นผลอันดับหนึ่งของ first-stage ก็ตาม
      var grounding = Math.min(1, cov + 0.35 * title + 0.22 * exact);
      candidates[c].grounding = grounding;

      if (cfg.USE_RERANK) {
        var score =
          cov * (0.60 + 0.15 * firstNorm) +
          cfg.RERANK_TITLE_BOOST * title +
          cfg.RERANK_TAG_BOOST * tag +
          cfg.RERANK_EXACT_TERM_BOOST * exact;

        // ชิ้นแรกของเอกสาร (part 1) มักเป็นนิยาม จึงให้โบนัสเล็กน้อยกับคำถามสั้น
        if (ch.part === 1 && qBase.length <= 24) score += 0.04;

        candidates[c].score = Math.min(1, score);
      } else {
        // ปิด rerank : ใช้อันดับจากชั้นแรกตรง ๆ (normalize ให้อยู่ช่วง 0..1 เพื่อแสดงผล)
        candidates[c].score = maxFirst ? (candidates[c].firstStageScore / maxFirst) : 0;
      }

      candidates[c].signals = {
        coverage: +cov.toFixed(3),
        firstStage: +firstNorm.toFixed(3),
        title: +title.toFixed(2),
        tag: tag,
        exactTerm: +exact.toFixed(2),
        grounding: +grounding.toFixed(3)
      };
    }

    if (cfg.USE_RERANK) {
      candidates.sort(function (x, y) { return y.score - x.score; });
    }
    for (var k = 0; k < candidates.length; k++) {
      candidates[k].rankAfter = k + 1;
      candidates[k].moved = candidates[k].rankBefore - candidates[k].rankAfter;
    }
    return candidates;
  }

  return { rerank: rerank, coverage: coverage };
})();
