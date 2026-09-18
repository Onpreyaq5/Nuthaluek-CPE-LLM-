/* =============================================================
 *  rag-generate.js — Stage 7-8 : Guardrail + Answer Generation
 *
 *  แก้ปัญหา 08 (Hallucination / ตอบทั้งที่ไม่มีหลักฐาน / ไม่มีแหล่งอ้างอิง)
 *  แก้ปัญหา 10 (ให้คำแนะนำการลงทุนรายบุคคล และข้อมูลล้าสมัย)
 *
 *  ลำดับการทำงาน
 *   1) Safety Guard      : คำถามขอคำแนะนำลงทุนรายบุคคล -> ปฏิเสธก่อนเข้าขั้นตอนอื่น
 *   2) Grounding Check   : คะแนนหลักฐานต่ำกว่าเกณฑ์ -> ตอบว่าไม่พบข้อมูล ไม่เดา
 *   3) Compose           : เรียบเรียงคำตอบ "จากบริบทเท่านั้น"
 *   4) Citation          : แนบรหัสเอกสารที่ใช้ทุกครั้ง
 *   5) Faithfulness      : วัดว่าคำตอบมีเนื้อหาที่ตรวจสอบกลับไปยังบริบทได้จริงแค่ไหน
 *   6) Freshness         : เตือนเมื่อเอกสารเก่าเกินเกณฑ์
 * ============================================================= */

window.RagGenerate = (function () {

  /* ---------- 1) Safety Guard ---------- */
  function safetyCheck(rawQuery) {
    if (!window.RAG_CONFIG.SAFETY_GUARD) return null;
    var q = window.RagNormalize.normalizeText(rawQuery);
    var pats = window.SAFETY_PATTERNS || [];
    for (var i = 0; i < pats.length; i++) {
      var p = window.RagNormalize.normalizeText(pats[i]);
      if (p && q.indexOf(p) !== -1) {
        return {
          blocked: true,
          matched: pats[i],
          text:
            "ระบบนี้เป็นฐานความรู้เพื่อการศึกษา จึงไม่สามารถให้คำแนะนำการลงทุนรายบุคคล " +
            "ทำนายราคา หรือระบุสินทรัพย์ที่ควรซื้อขายได้\n\n" +
            "สิ่งที่ระบบช่วยได้คือการอธิบายหลักการ เช่น\n" +
            "• วิธีคำนวณขนาดสถานะจากความเสี่ยงที่รับได้\n" +
            "• หลักการวางจุดตัดขาดทุนตามโครงสร้างราคาและค่า ATR\n" +
            "• วิธีประเมินว่าระบบเทรดมีความได้เปรียบจริงหรือไม่ด้วยค่า Expectancy\n\n" +
            "ลองถามใหม่ในเชิงหลักการได้เลย เช่น \"คำนวณขนาดสถานะอย่างไร\""
        };
      }
    }
    return null;
  }

  /* ---------- 2) ตรวจความสดของข้อมูล ---------- */
  function freshnessWarning(contexts) {
    if (!window.RAG_CONFIG.FRESHNESS_WARNING) return null;
    var limit = window.RAG_CONFIG.FRESHNESS_MONTHS;
    var now = new Date();
    var stale = [];

    for (var i = 0; i < contexts.length; i++) {
      var u = contexts[i].chunk.updated;
      if (!u) continue;
      var parts = u.split("-");
      var y = parseInt(parts[0], 10), m = parseInt(parts[1], 10);
      if (!y || !m) continue;
      var months = (now.getFullYear() - y) * 12 + (now.getMonth() + 1 - m);
      if (months > limit) stale.push(contexts[i].chunk.docId + " (" + u + ")");
    }
    if (!stale.length) return null;
    return "ข้อมูลอ้างอิงบางส่วนทบทวนล่าสุดเมื่อ " + stale.join(", ") +
           " ซึ่งเกิน " + limit + " เดือน ควรตรวจสอบประกาศล่าสุดก่อนนำไปใช้";
  }

  /* ---------- 3) วัด Faithfulness ---------- *
   * วัดว่าเนื้อหาในคำตอบตรวจสอบกลับไปหาบริบทได้กี่เปอร์เซ็นต์
   * ถ้าค่าต่ำ แปลว่าคำตอบมีเนื้อหาที่ "ไม่ได้มาจากเอกสาร" ซึ่งคือสัญญาณ Hallucination
   */
  function faithfulness(answer, contexts) {
    var ansTokens = window.RagNormalize.tokenize(answer);
    if (!ansTokens.length) return 0;

    var ctxSet = {};
    for (var i = 0; i < contexts.length; i++) {
      var t = window.RagNormalize.tokenize(contexts[i].chunk.fullAnswer + " " + contexts[i].chunk.q);
      for (var j = 0; j < t.length; j++) ctxSet[t[j]] = true;
    }
    var hit = 0;
    for (var k = 0; k < ansTokens.length; k++) {
      if (ctxSet[ansTokens[k]]) hit++;
    }
    return hit / ansTokens.length;
  }

  /* ---------- 4) เรียบเรียงคำตอบจากบริบท ---------- */
  function compose(rawQuery, contexts) {
    var top = contexts[0].chunk;
    var out = top.fullAnswer;

    // เอกสารสนับสนุนอื่น ๆ ที่เป็นคนละเรื่องกับชิ้นแรก
    var related = [];
    var seen = {};
    seen[top.docId] = true;
    for (var i = 1; i < contexts.length; i++) {
      var c = contexts[i].chunk;
      if (seen[c.docId]) continue;
      seen[c.docId] = true;
      related.push({ id: c.docId, q: c.q });
    }

    if (related.length) {
      out += "\n\nหัวข้อที่เกี่ยวข้องซึ่งอยู่ในฐานความรู้เดียวกัน";
      for (var r = 0; r < related.length; r++) {
        out += "\n• " + related[r].q + "  [" + related[r].id + "]";
      }
    }
    return out;
  }

  /* ---------- 5) เรียก LLM จริง (ทางเลือก) ---------- */
  function buildPrompt(rawQuery, contexts) {
    var ctx = "";
    for (var i = 0; i < contexts.length; i++) {
      var c = contexts[i].chunk;
      ctx += "[" + c.docId + "] หัวข้อ: " + c.q + "\n" + c.fullAnswer + "\n\n";
    }
    return (
      "คุณเป็นผู้ช่วยตอบคำถามเรื่องการเทรดเพื่อการศึกษา\n" +
      "กฎที่ต้องทำตามอย่างเคร่งครัด\n" +
      "1. ตอบโดยใช้ข้อมูลจาก \"บริบท\" ด้านล่างเท่านั้น ห้ามเพิ่มข้อมูลจากความรู้ภายนอก\n" +
      "2. ถ้าบริบทไม่มีคำตอบ ให้ตอบว่าไม่พบข้อมูลในฐานความรู้ ห้ามเดา\n" +
      "3. แนบรหัสเอกสารที่ใช้ เช่น [I02] ต่อท้ายประโยคที่อ้างอิง\n" +
      "4. ห้ามให้คำแนะนำการลงทุนรายบุคคลหรือทำนายราคา\n" +
      "5. ตอบเป็นภาษาไทย กระชับ อ่านง่าย\n\n" +
      "บริบท\n" + ctx +
      "คำถาม: " + rawQuery + "\nคำตอบ:"
    );
  }

  function callLLM(rawQuery, contexts) {
    var cfg = window.RAG_CONFIG;
    var prompt = buildPrompt(rawQuery, contexts);
    var key = cfg.LLM_API_KEY;
    if (!key) return Promise.reject(new Error("ยังไม่ได้ใส่ API Key"));

    if (cfg.LLM_PROVIDER === "gemini") {
      var url = "https://generativelanguage.googleapis.com/v1beta/models/" +
        encodeURIComponent(cfg.LLM_MODEL) + ":generateContent?key=" + encodeURIComponent(key);
      return fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] })
      })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (j.error) throw new Error(j.error.message || "LLM error");
          var cand = j.candidates && j.candidates[0];
          var part = cand && cand.content && cand.content.parts && cand.content.parts[0];
          if (!part || !part.text) throw new Error("LLM ไม่ส่งข้อความกลับมา");
          return part.text;
        });
    }

    // OpenAI-compatible
    return fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + key },
      body: JSON.stringify({
        model: cfg.LLM_MODEL,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.2
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.error) throw new Error(j.error.message || "LLM error");
        return j.choices[0].message.content;
      });
  }

  /* ---------- 6) ฟังก์ชันหลัก ---------- */
  function generate(rawQuery, ranked) {
    var cfg = window.RAG_CONFIG;
    var info = {
      refused: false,
      reason: "",
      citations: [],
      faithfulness: 0,
      topScore: 0,
      freshness: null,
      safety: null
    };

    // 1) Safety Guard
    var safety = safetyCheck(rawQuery);
    if (safety) {
      info.refused = true;
      info.reason = "safety";
      info.safety = safety.matched;
      return { text: safety.text, info: info };
    }

    // 2) ไม่มีผลลัพธ์เลย
    if (!ranked || !ranked.length) {
      info.refused = true;
      info.reason = "no-result";
      return {
        text: "ไม่พบข้อมูลที่เกี่ยวข้องในฐานความรู้เรื่องการเทรด\n\n" +
              "ลองพิมพ์คำถามใหม่โดยใช้คำสำคัญ เช่น RSI, MACD, แนวรับแนวต้าน, " +
              "การบริหารความเสี่ยง, Order Block หรือ Backtesting",
        info: info
      };
    }

    var contexts = ranked.slice(0, cfg.TOP_K_CONTEXT);
    // ใช้ "คะแนนหลักฐาน" (grounding) ไม่ใช่ "คะแนนจัดอันดับ" (score)
    // เพราะคะแนนจัดอันดับบอกแค่ว่าชิ้นไหนดีที่สุดในกลุ่มที่ค้นมาได้
    // แต่ไม่ได้บอกว่าดีพอที่จะใช้ตอบหรือยัง ซึ่งเป็นคนละคำถามกัน
    info.topScore = (contexts[0].grounding != null) ? contexts[0].grounding : contexts[0].score;

    // 3) Grounding Check — หัวใจของการกัน Hallucination
    if (info.topScore < cfg.GROUNDING_THRESHOLD) {
      info.refused = true;
      info.reason = "low-grounding";
      var hints = [];
      for (var h = 0; h < Math.min(3, ranked.length); h++) hints.push(ranked[h].chunk.q);
      return {
        text: "ไม่พบข้อมูลที่สนับสนุนคำตอบมากพอในฐานความรู้ (คะแนนหลักฐานสูงสุด " +
              info.topScore.toFixed(3) + " ต่ำกว่าเกณฑ์ " + cfg.GROUNDING_THRESHOLD + ")\n\n" +
              "ระบบเลือกที่จะไม่เดาคำตอบ เพราะการตอบทั้งที่ไม่มีหลักฐานคือสาเหตุหลักของ Hallucination\n\n" +
              "หัวข้อที่ใกล้เคียงที่สุดที่มีอยู่จริงในฐานความรู้\n• " + hints.join("\n• "),
        info: info
      };
    }

    // 4) เรียบเรียงคำตอบ
    var text = compose(rawQuery, contexts);

    // 5) แนบแหล่งอ้างอิง
    var ids = [];
    for (var i = 0; i < contexts.length; i++) {
      if (ids.indexOf(contexts[i].chunk.docId) === -1) ids.push(contexts[i].chunk.docId);
    }
    info.citations = ids;
    if (cfg.REQUIRE_CITATION) {
      text += "\n\nแหล่งอ้างอิงจากฐานความรู้: " + ids.map(function (x) { return "[" + x + "]"; }).join(" ");
    }

    // 6) Faithfulness + Freshness
    info.faithfulness = faithfulness(text, contexts);
    info.freshness = freshnessWarning(contexts);
    if (info.freshness) text += "\n\nหมายเหตุ: " + info.freshness;

    return { text: text, info: info };
  }

  return {
    generate: generate,
    safetyCheck: safetyCheck,
    faithfulness: faithfulness,
    buildPrompt: buildPrompt,
    callLLM: callLLM
  };
})();
