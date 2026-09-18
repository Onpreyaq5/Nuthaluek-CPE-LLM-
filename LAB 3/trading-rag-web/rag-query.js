/* =============================================================
 *  rag-query.js — Stage 4 : Query Understanding & Transformation
 *
 *  แก้ปัญหา 03 (Vocabulary Mismatch) และ 04 (คำถามสั้น กำกวม สะกดไม่ตรง)
 *
 *  ทำ 3 อย่าง
 *   1) Normalize   : ทำความสะอาดคำถามให้อยู่รูปเดียวกับตอนทำดัชนี
 *   2) Synonym     : ขยายคำพ้อง ไทย <-> อังกฤษ  ("ดัชนีกำลังสัมพัทธ์" -> เพิ่ม "rsi")
 *   3) Multi-Query : สร้างหลายมุมมองของคำถามเดียว แล้วรวมผลการค้น
 * ============================================================= */

window.RagQuery = (function () {

  /* สร้างตารางค้นคำพ้องแบบ 2 ทาง จาก TRADING_SYNONYMS */
  var SYN_MAP = null;
  function buildSynMap() {
    if (SYN_MAP) return SYN_MAP;
    SYN_MAP = [];
    var groups = window.TRADING_SYNONYMS || [];
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i].map(function (w) {
        return window.RagNormalize.normalizeText(w);
      });
      SYN_MAP.push(g);
    }
    return SYN_MAP;
  }

  /* ---------- 1) ขยายคำพ้อง ---------- *
   * ถ้าคำถามมีสมาชิกตัวใดตัวหนึ่งของกลุ่ม จะเติมสมาชิกที่เหลือเข้าไปในคำค้น
   * ทำให้ "อยากรู้เรื่องดัชนีกำลังสัมพัทธ์" ค้นเจอเอกสารที่เขียนว่า RSI ได้
   */
  function expandSynonyms(query) {
    var q = window.RagNormalize.normalizeText(query);
    var map = buildSynMap();
    var added = [];

    for (var i = 0; i < map.length; i++) {
      var group = map[i];
      var hit = false;
      for (var j = 0; j < group.length; j++) {
        if (group[j] && q.indexOf(group[j]) !== -1) { hit = true; break; }
      }
      if (hit) {
        for (var k = 0; k < group.length; k++) {
          if (group[k] && q.indexOf(group[k]) === -1) added.push(group[k]);
        }
      }
    }
    return { expanded: added, text: added.length ? (q + " " + added.join(" ")) : q };
  }

  /* ---------- 2) Multi-Query ---------- *
   * คำถามสั้น เช่น "RSI" ให้ข้อมูลน้อยเกินไป
   * จึงสร้างรูปแบบคำถามเพิ่ม เพื่อให้ค้นเจอเอกสารที่เขียนคนละสำนวน
   */
  function multiQuery(query) {
    var base = window.RagNormalize.normalizeText(query);
    var variants = [base];

    // ถ้าเป็นคำถามสั้นมาก (เช่นพิมพ์แค่ชื่ออินดิเคเตอร์) ให้เติมบริบท
    if (base.length <= 18) {
      variants.push(base + " คืออะไร");
      variants.push(base + " ใช้อย่างไร วิธีใช้");
      variants.push("ความหมายของ " + base);
    } else {
      // คำถามยาว ให้สร้างรูปแบบที่เน้นคำสำคัญ (ตัดคำถามนำออก)
      var stripped = base
        .replace(/^(ช่วย|ขอ|อยากรู้|อยากทราบ|ถามหน่อย|รบกวน)\s*/g, "")
        .replace(/(คืออะไร|คือ อะไร|หมายถึงอะไร|ยังไง|อย่างไร|ไหม|หรือไม่|ครับ|ค่ะ|หน่อย)/g, " ")
        .replace(/\s+/g, " ")
        .trim();
      if (stripped && stripped !== base) variants.push(stripped);
    }
    return variants;
  }

  /* ---------- 3) ฟังก์ชันหลัก ---------- */
  function transform(rawQuery) {
    var cfg = window.RAG_CONFIG;
    var trace = { raw: rawQuery, steps: [] };

    var q = cfg.QUERY_NORMALIZE
      ? window.RagNormalize.normalizeText(rawQuery)
      : String(rawQuery);
    trace.steps.push({ name: "Normalize", value: q });

    var synInfo = { expanded: [], text: q };
    if (cfg.QUERY_SYNONYM_EXPANSION) {
      synInfo = expandSynonyms(q);
      trace.steps.push({
        name: "Synonym Expansion",
        value: synInfo.expanded.length ? synInfo.expanded.join(", ") : "(ไม่พบคำพ้องที่ตรง)"
      });
    }

    var variants = [synInfo.text];
    if (cfg.QUERY_MULTI) {
      var mv = multiQuery(q);
      for (var i = 0; i < mv.length; i++) {
        var candidate = cfg.QUERY_SYNONYM_EXPANSION
          ? expandSynonyms(mv[i]).text
          : mv[i];
        if (variants.indexOf(candidate) === -1) variants.push(candidate);
      }
      trace.steps.push({ name: "Multi-Query", value: variants.length + " รูปแบบ" });
    }

    return {
      base: q,                 // คำถามเดิมหลัง normalize (ยังไม่ขยายคำพ้อง)
      main: synInfo.text,      // คำถามหลังขยายคำพ้อง
      variants: variants,      // ทุกมุมมองของคำถาม
      synonyms: synInfo.expanded,
      trace: trace
    };
  }

  return {
    transform: transform,
    expandSynonyms: expandSynonyms,
    multiQuery: multiQuery
  };
})();
