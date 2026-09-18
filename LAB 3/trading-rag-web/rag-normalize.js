/* =============================================================
 *  rag-normalize.js — Stage 1 : Data Cleaning & Tokenization
 *
 *  แก้ปัญหา 01 (Data Quality) และเป็นฐานของปัญหา 03 (Vocabulary Mismatch)
 *  ภาษาไทยไม่มีช่องว่างระหว่างคำ จึงใช้ character n-gram แทนการตัดคำด้วยพจนานุกรม
 * ============================================================= */

window.RagNormalize = (function () {

  /* ---------- 1) ทำความสะอาดข้อความ ---------- */
  function normalizeText(s) {
    if (!s) return "";
    if (!window.RAG_CONFIG.NORMALIZE_TEXT) return String(s);

    return String(s)
      .toLowerCase()
      // เครื่องหมายวรรคตอน -> ช่องว่าง (เก็บ . ไว้สำหรับตัวเลขทศนิยม)
      .replace(/[“”"'`?!,;:()\[\]{}<>|/\\+*#%&@~^=]/g, " ")
      // ยุบ "ๆๆๆ" หรือตัวอักษรซ้ำเกิน 2 ตัว ให้เหลือ 2 ตัว
      .replace(/(.)\1{2,}/g, "$1$1")
      // ยุบช่องว่างทุกชนิดให้เหลือช่องเดียว
      .replace(/\s+/g, " ")
      .trim();
  }

  /* ---------- 2) ตัดคำ / สร้าง token ---------- *
   * - อังกฤษ+ตัวเลข : ตัดเป็นคำตรง ๆ (เช่น "rsi", "14", "61.8")
   * - ไทย           : ตัดเป็น character n-gram ขนาด NGRAM_MIN..NGRAM_MAX
   *                   เพราะไทยเขียนติดกัน การใช้ n-gram ทำให้จับคำย่อยได้
   *                   เช่น "แนวรับ" -> แน, นว, วร, รับ, แนว, นวร, วรับ
   */
  function tokenize(s) {
    var text = normalizeText(s);
    var tokens = [];
    var cfg = window.RAG_CONFIG;

    // 2.1 คำภาษาอังกฤษและตัวเลข
    var latin = text.match(/[a-z0-9]+(?:\.[0-9]+)?/g) || [];
    for (var i = 0; i < latin.length; i++) {
      if (latin[i].length >= 1) tokens.push(latin[i]);
    }

    // 2.2 ช่วงตัวอักษรไทย -> n-gram
    var thaiRuns = text.match(/[\u0E00-\u0E7F]+/g) || [];
    for (var r = 0; r < thaiRuns.length; r++) {
      var run = thaiRuns[r];
      for (var n = cfg.NGRAM_MIN; n <= cfg.NGRAM_MAX; n++) {
        if (run.length < n) continue;
        for (var j = 0; j + n <= run.length; j++) {
          tokens.push(run.substr(j, n));
        }
      }
    }
    return tokens;
  }

  /* ---------- 3) ลายนิ้วมือเอกสาร ใช้ตรวจข้อมูลซ้ำ ---------- */
  function fingerprint(doc) {
    var base = normalizeText((doc.q || "") + " " + (doc.a || ""));
    return base.replace(/\s/g, "").slice(0, 160);
  }

  /* ---------- 4) ตรวจและตัดเอกสารซ้ำ ---------- *
   * คืนค่าเป็น { docs, removed, issues } เพื่อให้หน้า Problem Lab เอาไปแสดงได้
   */
  function dedupe(docs) {
    var seen = {};
    var kept = [];
    var removed = [];
    var issues = [];

    for (var i = 0; i < docs.length; i++) {
      var d = docs[i];

      // ตรวจคุณภาพข้อมูลเบื้องต้น (Data Quality Check)
      if (!d.q || !d.a) {
        issues.push({ id: d.id, type: "ข้อมูลไม่ครบ", detail: "ไม่มีคำถามหรือคำตอบ" });
        continue;
      }
      if (d.a.length < 40) {
        issues.push({ id: d.id, type: "คำตอบสั้นผิดปกติ", detail: d.a.length + " ตัวอักษร" });
      }
      if (!d.cat || !d.level) {
        issues.push({ id: d.id, type: "Metadata ไม่ครบ", detail: "ขาด cat หรือ level" });
      }

      var fp = fingerprint(d);
      if (window.RAG_CONFIG.DEDUPE_DOCS && seen[fp]) {
        removed.push({ id: d.id, duplicateOf: seen[fp] });
        continue;
      }
      seen[fp] = d.id;
      kept.push(d);
    }
    return { docs: kept, removed: removed, issues: issues };
  }

  /* ---------- 5) แบ่งคำถามสำรองเป็น 2 ชุด : เข้าดัชนี กับ กันไว้ทดสอบ ----------
   * ปัญหาที่แก้ด้วยฟังก์ชันนี้คือ Test Set Leakage (ชุดทดสอบรั่ว)
   * ถ้าเอาคำถามสำรองไปใส่ในดัชนีทั้งหมด แล้วใช้คำถามชุดเดียวกันมาวัดผล
   * ระบบจะได้คะแนนเกือบเต็มเสมอ เพราะเป็นการค้นหาข้อความที่ตรงกันทุกตัวอักษร
   * ตัวเลขที่ได้จึงไม่ได้บอกความสามารถจริงของ Retrieval เลย
   *
   * วิธีแบ่ง : ลำดับคู่ (0,2,4...) เข้าดัชนี  ลำดับคี่ (1,3,5...) กันไว้เป็นชุดทดสอบ
   * ทั้งสองฝั่งจึงไม่มีทางทับกัน และทุกส่วนของระบบต้องเรียกฟังก์ชันนี้ตัวเดียวกัน
   */
  function splitAlt(alt) {
    var indexed = [], heldOut = [];
    var list = alt || [];
    for (var i = 0; i < list.length; i++) {
      if (i % 2 === 0) indexed.push(list[i]); else heldOut.push(list[i]);
    }
    return { indexed: indexed, heldOut: heldOut };
  }

  /* ---------- 6) ตัวช่วย : นับความถี่ของ token ---------- */
  function termFreq(tokens) {
    var tf = {};
    for (var i = 0; i < tokens.length; i++) {
      tf[tokens[i]] = (tf[tokens[i]] || 0) + 1;
    }
    return tf;
  }

  return {
    normalizeText: normalizeText,
    tokenize: tokenize,
    fingerprint: fingerprint,
    dedupe: dedupe,
    splitAlt: splitAlt,
    termFreq: termFreq
  };
})();
