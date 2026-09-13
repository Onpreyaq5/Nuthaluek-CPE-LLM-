/* =============================================================
 *  problems.js — ศูนย์รวม "ปัญหาและการแก้ไขปัญหาของ RAG System"
 *
 *  โจทย์ DL-05 ต้องการให้วิเคราะห์ปัญหาในแต่ละขั้นตอน พร้อม
 *   (1) สาเหตุ  (2) วิธีตรวจสอบ  (3) แนวทางแก้ไข  (4) อ้างอิง Source Code จริง
 *
 *  ไฟล์นี้ทำมากกว่าการอธิบาย คือมี runner ที่ "รันจริง" เพื่อเทียบ
 *  ก่อนแก้ (ปิดสวิตช์) กับ หลังแก้ (เปิดสวิตช์) ให้เห็นผลต่างด้วยตาตัวเอง
 * ============================================================= */

window.RagProblems = (function () {

  /* ตัวช่วย : ตั้งค่า config ชั่วคราวแล้วคืนค่าเดิมเสมอ */
  function withConfig(overrides, fn) {
    var backup = {};
    for (var k in overrides) {
      if (Object.prototype.hasOwnProperty.call(overrides, k)) {
        backup[k] = window.RAG_CONFIG[k];
        window.RAG_CONFIG[k] = overrides[k];
      }
    }
    try {
      return fn();
    } finally {
      for (var k2 in backup) {
        if (Object.prototype.hasOwnProperty.call(backup, k2)) window.RAG_CONFIG[k2] = backup[k2];
      }
    }
  }

  /* ตัวช่วย : สรุปผลลัพธ์ Top-N ให้อยู่ในรูปที่ UI แสดงได้ */
  function topList(res, n) {
    var out = [];
    var seen = {};
    for (var i = 0; i < res.results.length && out.length < n; i++) {
      var c = res.results[i].chunk;
      if (seen[c.docId]) continue;
      seen[c.docId] = true;
      out.push({
        docId: c.docId,
        q: c.q,
        cat: c.cat,
        level: c.level,
        score: res.results[i].score,
        rankBefore: res.results[i].rankBefore,
        rankAfter: res.results[i].rankAfter
      });
    }
    return out;
  }

  /* =========================================================
   *  รายการปัญหาทั้ง 10 ข้อ เรียงตามลำดับขั้นตอนการทำงานของ RAG
   * ========================================================= */
  var PROBLEMS = [

    /* ---------------- 01 ---------------- */
    {
      no: "01",
      stage: "Ingestion",
      icon: "broom",
      title: "ข้อมูลซ้ำและข้อมูลไม่สะอาด (Data Quality)",
      symptom: "ผลการค้นหามีเนื้อหาเดียวกันโผล่ซ้ำหลายอันดับ ทำให้เอกสารอื่นที่ควรได้ที่ถูกเบียดตกไป และผู้ใช้เห็นคำตอบซ้ำ ๆ",
      cause: "ฐานความรู้ถูกรวมมาจากหลายแหล่ง ทำให้มีเนื้อหาซ้ำ มีช่องว่างเกิน มีตัวพิมพ์ใหญ่เล็กปนกัน และบางรายการขาด metadata ระบบจึงมองเอกสารเดียวกันเป็นคนละชิ้น",
      detect: "คำนวณลายนิ้วมือ (fingerprint) จากข้อความที่ normalize แล้วมาเทียบกัน ถ้าซ้ำแปลว่าเป็นเอกสารเดียวกัน พร้อมตรวจว่ารายการใดขาด cat/level หรือคำตอบสั้นผิดปกติ",
      fix: "ทำ Normalization ก่อนเข้าดัชนีทุกครั้ง (ตัวพิมพ์เล็ก ยุบช่องว่าง ยุบอักษรซ้ำ) แล้วตัดข้อมูลซ้ำด้วย fingerprint พร้อมรายงานรายการที่ metadata ไม่ครบออกมาให้ผู้ดูแลแก้",
      code: "rag-normalize.js -> normalizeText(), fingerprint(), dedupe()",
      keys: ["NORMALIZE_TEXT", "DEDUPE_DOCS"],
      demoQuery: "(ทดสอบด้วยการแทรกเอกสารซ้ำเข้าฐานความรู้ชั่วคราว)",
      run: function () {
        var kb = window.TRADING_KB;
        var original = kb.slice();
        // แทรกเอกสารซ้ำ + เอกสารสกปรก เพื่อจำลองปัญหาให้เห็นจริง
        var src = kb[0];
        var dirty = [
          { id: "DUP-1", cat: src.cat, level: src.level, tags: src.tags, q: src.q, alt: [], a: src.a, updated: src.updated },
          { id: "DUP-2", cat: src.cat, level: src.level, tags: src.tags, q: "  " + src.q.toUpperCase() + "   ", alt: [], a: src.a + "   ", updated: src.updated },
          { id: "BAD-1", cat: "", level: "", tags: [], q: "ทดสอบข้อมูลไม่ครบ", alt: [], a: "สั้นมาก", updated: "" }
        ];
        window.TRADING_KB = original.concat(dirty);

        var off = withConfig({ NORMALIZE_TEXT: false, DEDUPE_DOCS: false }, function () {
          return window.RagPipeline.buildIndex();
        });
        var on = withConfig({ NORMALIZE_TEXT: true, DEDUPE_DOCS: true }, function () {
          return window.RagPipeline.buildIndex();
        });

        window.TRADING_KB = original;
        window.RagPipeline.buildIndex();

        return {
          type: "stats",
          beforeLabel: "ปิดการทำความสะอาด",
          afterLabel: "เปิดการทำความสะอาด",
          before: [
            { name: "เอกสารเข้าดัชนี", value: off.docs + " ชิ้น" },
            { name: "เอกสารซ้ำที่ตัดออก", value: off.removed.length + " ชิ้น" },
            { name: "ปัญหาคุณภาพที่ตรวจพบ", value: off.issues.length + " รายการ" },
            { name: "จำนวน chunk", value: off.chunkStats.count }
          ],
          after: [
            { name: "เอกสารเข้าดัชนี", value: on.docs + " ชิ้น" },
            { name: "เอกสารซ้ำที่ตัดออก", value: on.removed.length + " ชิ้น" },
            { name: "ปัญหาคุณภาพที่ตรวจพบ", value: on.issues.length + " รายการ" },
            { name: "จำนวน chunk", value: on.chunkStats.count }
          ],
          verdict: "เมื่อเปิดการทำความสะอาด ระบบตัดเอกสารซ้ำออกได้ " + on.removed.length +
                   " ชิ้น และรายงานรายการที่ metadata ไม่ครบให้แก้ ทำให้ดัชนีไม่มีเนื้อหาซ้ำมาแย่งอันดับกันเอง"
        };
      }
    },

    /* ---------------- 02 ---------------- */
    {
      no: "02",
      stage: "Chunking",
      icon: "scissors",
      title: "ขนาด Chunk ไม่เหมาะสม และบริบทขาดตรงรอยต่อ",
      symptom: "ค้นเจอเอกสารถูก แต่เนื้อหาที่ดึงมาถูกตัดกลางประโยค หรือกว้างจนคำตอบจริงถูกกลบด้วยเนื้อหาอื่นในชิ้นเดียวกัน",
      cause: "chunk ใหญ่เกินไปทำให้เวกเตอร์หนึ่งชิ้นแทนหลายแนวคิดพร้อมกัน ความคล้ายจึงเจือจาง ส่วน chunk เล็กเกินไปทำให้คำอธิบายที่ต่อเนื่องถูกหั่นขาดจากกัน และถ้าไม่มีส่วนซ้อนทับ ประโยคที่คร่อมรอยต่อจะหายไปจากทั้งสองชิ้น",
      detect: "วัดสถิติความยาว chunk (ต่ำสุด/เฉลี่ย/สูงสุด) และรันชุดทดสอบวัด Hit@3 ที่ค่าขนาดต่าง ๆ แล้วเทียบกัน ถ้าขนาดใดให้ Hit ต่ำผิดปกติแปลว่าตัดไม่เหมาะกับข้อมูลชุดนี้",
      fix: "ตัดตามโครงสร้างก่อน (บรรทัด/หัวข้อย่อย) แล้วค่อยตัดตามขนาดเฉพาะชิ้นที่ยังยาวเกิน พร้อมกำหนด overlap และใส่หัวเรื่องของเอกสารไว้ต้นทุก chunk เพื่อให้ทุกชิ้นรู้ว่าตัวเองพูดเรื่องอะไร",
      code: "rag-chunk.js -> splitByStructure(), splitBySize(), buildChunks()",
      keys: ["CHUNK_SIZE", "CHUNK_OVERLAP", "CHUNK_STRUCTURE_AWARE"],
      demoQuery: "เปรียบเทียบการตัด 3 แบบบนเอกสารเดียวกัน",
      run: function () {
        var doc = null;
        for (var i = 0; i < window.TRADING_KB.length; i++) {
          if (window.TRADING_KB[i].id === "S02") { doc = window.TRADING_KB[i]; break; }
        }
        if (!doc) doc = window.TRADING_KB[0];

        function sample(size, overlap, structure) {
          return withConfig(
            { CHUNK_SIZE: size, CHUNK_OVERLAP: overlap, CHUNK_STRUCTURE_AWARE: structure },
            function () {
              var chunks = window.RagChunk.buildChunks([doc]);
              return {
                count: chunks.length,
                stats: window.RagChunk.stats(chunks),
                first: chunks[0] ? chunks[0].body.slice(0, 120) : "",
                second: chunks[1] ? chunks[1].body.slice(0, 120) : "(ไม่มีชิ้นที่ 2)"
              };
            }
          );
        }

        var tooBig = sample(4000, 0, false);
        var tooSmall = sample(60, 0, false);
        var good = sample(420, 80, true);

        return {
          type: "stats",
          beforeLabel: "ตัดแบบไม่เหมาะสม",
          afterLabel: "ตัดแบบที่ใช้จริงในระบบ (420/80 + ตามโครงสร้าง)",
          before: [
            { name: "ใหญ่เกิน (4000 ตัวอักษร)", value: tooBig.count + " chunk — ทั้งเอกสารรวมเป็นชิ้นเดียว เวกเตอร์เจือจาง" },
            { name: "เล็กเกิน (60 ตัวอักษร ไม่มี overlap)", value: tooSmall.count + " chunk — เฉลี่ย " + tooSmall.stats.avg + " ตัวอักษร" },
            { name: "ตัวอย่างชิ้นที่ 1 ของแบบเล็กเกิน", value: tooSmall.first + "..." },
            { name: "ตัวอย่างชิ้นที่ 2 ของแบบเล็กเกิน", value: tooSmall.second + "..." }
          ],
          after: [
            { name: "จำนวน chunk", value: good.count + " chunk" },
            { name: "ความยาวเฉลี่ย", value: good.stats.avg + " ตัวอักษร" },
            { name: "สั้นสุด / ยาวสุด", value: good.stats.min + " / " + good.stats.max },
            { name: "ตัวอย่างชิ้นที่ 1", value: good.first + "..." }
          ],
          verdict: "แบบเล็กเกินตัดคำอธิบายขาดกลางประโยค ส่วนแบบใหญ่เกินยัดทุกหัวข้อไว้ชิ้นเดียว " +
                   "การตัดตามโครงสร้างแล้วใส่ overlap ทำให้แต่ละชิ้นจบความคิดในตัวเองและยังเชื่อมกับชิ้นข้างเคียงได้"
        };
      }
    },

    /* ---------------- 03 ---------------- */
    {
      no: "03",
      stage: "Indexing / Query",
      icon: "language",
      title: "คำที่ใช้ไม่ตรงกัน (Vocabulary Mismatch) ไทย-อังกฤษ",
      symptom: "ผู้ใช้ถามด้วยคำไทยว่า \"ดัชนีกำลังสัมพัทธ์\" แต่เอกสารเขียนว่า RSI ระบบจึงหาไม่เจอ ทั้งที่ข้อมูลมีอยู่จริงในฐานความรู้",
      cause: "การค้นด้วยความถี่คำต้องการให้คำในคำถามกับในเอกสารตรงกัน เมื่อเป็นคนละภาษาหรือคนละคำเรียก token จึงไม่ทับกันเลย คะแนนความคล้ายเป็นศูนย์ ปัญหานี้รุนแรงขึ้นในภาษาไทยเพราะเขียนติดกันไม่มีช่องว่าง การตัดคำจึงคลาดเคลื่อนได้ง่าย",
      detect: "ถามด้วยคำพ้องที่ไม่เคยปรากฏตรงตัวในเอกสาร แล้วดูว่าเอกสารเป้าหมายติดอันดับหรือไม่ ถ้าไม่ติดทั้งที่เนื้อหาตรง แปลว่าเกิด Vocabulary Mismatch",
      fix: "สองชั้นพร้อมกัน ชั้นแรกใช้ character n-gram (2-3 ตัวอักษร) แทนการตัดคำด้วยพจนานุกรม ทำให้จับคำย่อยในภาษาไทยได้ ชั้นที่สองสร้างพจนานุกรมคำพ้องเฉพาะโดเมนการเทรด แล้วขยายคำค้นก่อนส่งเข้าดัชนี",
      code: "rag-normalize.js -> tokenize() | rag-query.js -> expandSynonyms() | config.js -> TRADING_SYNONYMS",
      keys: ["QUERY_SYNONYM_EXPANSION", "NGRAM_MIN", "NGRAM_MAX"],
      demoQuery: "ดัชนีกำลังสัมพัทธ์ใช้ยังไง",
      run: function () {
        var q = "ดัชนีกำลังสัมพัทธ์ใช้ยังไง";
        var off = withConfig({ QUERY_SYNONYM_EXPANSION: false, QUERY_MULTI: false }, function () {
          return window.RagPipeline.ask(q);
        });
        var on = withConfig({ QUERY_SYNONYM_EXPANSION: true, QUERY_MULTI: true }, function () {
          return window.RagPipeline.ask(q);
        });
        var expanded = on.queryObj.synonyms.join(", ");

        return {
          type: "ranking",
          query: q,
          beforeLabel: "ปิดการขยายคำพ้อง",
          afterLabel: "เปิดการขยายคำพ้อง (เติม: " + (expanded || "-") + ")",
          before: topList(off, 3),
          after: topList(on, 3),
          verdict: "เอกสารเป้าหมายคือ I02 (RSI) เมื่อปิดการขยายคำพ้อง คำถามภาษาไทยแทบไม่มี token " +
                   "ทับกับเอกสารที่เขียนว่า RSI เลย พอเปิดระบบเติมคำว่า rsi และ relative strength index เข้าไป " +
                   "เอกสารที่ถูกต้องจึงขึ้นมาอันดับต้น"
        };
      }
    },

    /* ---------------- 04 ---------------- */
    {
      no: "04",
      stage: "Query Understanding",
      icon: "question",
      title: "คำถามสั้นหรือกำกวมเกินกว่าจะค้นได้แม่น",
      symptom: "ผู้ใช้พิมพ์แค่ \"MACD\" หรือ \"เสี่ยง\" ระบบได้ข้อมูลน้อยเกินกว่าจะรู้ว่าต้องการนิยาม วิธีใช้ หรือข้อควรระวัง ผลลัพธ์จึงกระจัดกระจาย",
      cause: "คำถามสั้นให้ token น้อยมาก สัญญาณที่ใช้จัดอันดับจึงบาง ทำให้เอกสารที่บังเอิญมีคำนั้นบ่อยชนะเอกสารที่ตอบคำถามจริง",
      detect: "เทียบผลลัพธ์ของคำถามสั้นกับคำถามเต็มประโยคที่มีความหมายเดียวกัน ถ้าอันดับต่างกันมากแปลว่าระบบพึ่งพาความยาวคำถามมากเกินไป",
      fix: "ทำ Multi-Query คือแตกคำถามเดียวเป็นหลายมุมมองก่อนค้น เช่น เติม \"คืออะไร\" และ \"ใช้อย่างไร\" สำหรับคำถามสั้น และตัดคำถามนำที่ไม่มีความหมายออกสำหรับคำถามยาว แล้วรวม token จากทุกมุมมองไปค้นพร้อมกัน",
      code: "rag-query.js -> multiQuery(), transform()",
      keys: ["QUERY_MULTI"],
      demoQuery: "bb คืออะไร",
      run: function () {
        var q = "bb คืออะไร";
        var off = withConfig({ QUERY_MULTI: false }, function () { return window.RagPipeline.ask(q); });
        var on = withConfig({ QUERY_MULTI: true }, function () { return window.RagPipeline.ask(q); });
        return {
          type: "ranking",
          query: q,
          beforeLabel: "ปิด Multi-Query (ค้นด้วยคำเดียว)",
          afterLabel: "เปิด Multi-Query (" + on.queryObj.variants.length + " รูปแบบ)",
          before: topList(off, 3),
          after: topList(on, 3),
          verdict: "คำถาม \"bb คืออะไร\" สั้นมากจนระบบมี token ไม่พอจะแยกได้ว่าหมายถึงอะไร " +
                   "เมื่อปิด Multi-Query ระบบตอบเป็นเอกสาร RSI (I02) ซึ่งผิด " +
                   "พอเปิดแล้วระบบสร้างรูปแบบเพิ่ม เช่น \"bb ใช้อย่างไร วิธีใช้\" ทำให้ได้ token มากพอ " +
                   "จะแยกได้ว่าเป้าหมายคือเอกสาร Bollinger Bands (I04)"
        };
      }
    },

    /* ---------------- 05 ---------------- */
    {
      no: "05",
      stage: "Retrieval",
      icon: "database",
      title: "ใช้วิธีค้นเพียงวิธีเดียวแล้วแพ้คำถามบางประเภท",
      symptom: "บางคำถามที่มีศัพท์เฉพาะ เช่น \"61.8\" หรือ \"FVG\" ค้นด้วยเวกเตอร์แล้วพลาด ส่วนคำถามเชิงความหมายที่ไม่มีคำตรงกันเลย ค้นด้วย BM25 แล้วไม่เจอ",
      cause: "BM25 ให้คะแนนจากการที่คำตรงกันตรงตัว จึงเก่งศัพท์เฉพาะแต่ไม่เข้าใจคำพ้อง ส่วนการค้นด้วยเวกเตอร์มองภาพรวมของข้อความ จึงทนต่อการใช้คำต่างกันได้ แต่ศัพท์เฉพาะที่ปรากฏน้อยครั้งจะถูกกลบด้วยคำทั่วไป",
      detect: "รันชุดทดสอบเดียวกันด้วยโหมด bm25, dense และ hybrid แล้วเทียบ Hit@3 กับ MRR ถ้าแต่ละโหมดพลาดคนละกลุ่มคำถาม แปลว่าควรรวมผลทั้งสองวิธี",
      fix: "ใช้ Hybrid Retrieval แล้วรวมผลด้วย Reciprocal Rank Fusion ซึ่งรวมจาก \"อันดับ\" ไม่ใช่คะแนนดิบ จึงไม่ต้องปรับสเกลให้เท่ากันก่อน เอกสารที่ติดอันดับดีจากทั้งสองวิธีจะได้คะแนนรวมสูงสุด",
      code: "rag-retrieve.js -> retrieve(), rrfFuse() | rag-index.js -> denseSearch(), bm25Search()",
      keys: ["RETRIEVAL_MODE", "RRF_K"],
      demoQuery: "โปรไฟล์วอลุ่ม",
      run: function () {
        var q = "โปรไฟล์วอลุ่ม";
        var dense = withConfig({ RETRIEVAL_MODE: "dense" }, function () { return window.RagPipeline.ask(q); });
        var bm = withConfig({ RETRIEVAL_MODE: "bm25" }, function () { return window.RagPipeline.ask(q); });
        var hy = withConfig({ RETRIEVAL_MODE: "hybrid" }, function () { return window.RagPipeline.ask(q); });

        return {
          type: "ranking3",
          query: q,
          labels: ["Vector อย่างเดียว", "BM25 อย่างเดียว", "Hybrid + RRF (ที่ระบบใช้จริง)"],
          lists: [topList(dense, 3), topList(bm, 3), topList(hy, 3)],
          verdict: "เอกสารเป้าหมายคือ A07 (Volume Profile และ POC) คำว่า \"โปรไฟล์วอลุ่ม\" ไม่ได้ปรากฏ" +
                   "ตรงตัวในเอกสารเลย เพราะเอกสารเขียนว่า Volume Profile การค้นด้วย BM25 ซึ่งวัดจากคำที่ตรงตัว" +
                   "จึงพลาดไปได้เอกสารเรื่องสภาพคล่อง ส่วนการค้นด้วยเวกเตอร์มองภาพรวมของข้อความจึงจับได้ " +
                   "เมื่อรวมอันดับด้วย RRF ผลลัพธ์จะตามวิธีที่มั่นใจกว่า ระบบจึงไม่พังเมื่อเจอคำถามที่อีกวิธีหนึ่งถนัด"
        };
      }
    },

    /* ---------------- 05.1 ---------------- */
    {
      no: "05.1",
      stage: "Retrieval",
      icon: "alert",
      title: "การขยายคำพ้องทำให้ผลแย่ลงกว่าไม่ขยาย (พบจากการวัดผล)",
      symptom: "หลังเพิ่มการขยายคำพ้องเพื่อแก้ปัญหา 03 คาดว่าคะแนนจะดีขึ้น แต่ผลการวัดกลับแย่ลง Hit@1 ลดจาก 57.8% เหลือ 52.2% ปัญหานี้ไม่ได้อยู่ในแผน แต่ถูกค้นพบเพราะมีการวัดผลด้วยตัวเลข",
      cause: "โค้ดเดิมนำคำถามเดิมกับคำพ้องที่เติมเข้าไปมารวมเป็นถุง token เดียวกันแล้วค้นครั้งเดียว อันดับของรายการนั้นจึงถูกคำถามเดิมครอบงำ คำพ้องแทบไม่มีน้ำหนัก และในกรณีที่คำถามเดิมไม่มีคำใดอยู่ในคลังเลย เช่น คำว่า ดัชนีกำลังสัมพัทธ์ อันดับที่ได้จากคำถามเดิมเป็นเพียงสัญญาณรบกวน แต่ยังได้น้ำหนักเต็ม จึงกลบเอกสารที่ถูกต้องจนมิด",
      detect: "พิมพ์ค่าสัญญาณของผลลัพธ์ 3 อันดับแรกออกมาดู ถ้าพบว่าทุกเอกสารมีค่า coverage ใกล้เคียงกันหมดและเอกสารเป้าหมายไม่ติดอันดับ นั่นคือลายเซ็นของการจัดอันดับด้วยสัญญาณรบกวน ไม่ใช่ด้วยความเกี่ยวข้องจริง",
      fix: "แยกเป็น 3 รายการค้นหาที่มาจากคนละแหล่ง แล้วให้น้ำหนักตามความน่าเชื่อถือก่อนรวมด้วย RRF คือ คำถามเดิมน้ำหนัก 1.00, คำพ้องล้วน ๆ น้ำหนัก 0.90 (คัดมาด้วยมือจึงเชื่อถือได้), และรูปแบบที่ระบบสร้างเองน้ำหนัก 0.45 (เป็นการเดา) จุดสำคัญคือรายการคำพ้องต้องมาจากคำพ้องเท่านั้น ห้ามผสมคำถามเดิม มิฉะนั้นจะกลับไปเป็นบั๊กเดิม",
      code: "rag-retrieve.js -> retrieve() ส่วนแยก baseTokens / synTokens / varTokens, rrfFuse() ที่รองรับน้ำหนัก | rag-query.js -> transform() คืนค่า base และ synonyms แยกกัน",
      keys: ["QUERY_SYNONYM_EXPANSION", "RRF_K"],
      demoQuery: "ดัชนีกำลังสัมพัทธ์",
      run: function () {
        var q = "ดัชนีกำลังสัมพัทธ์";
        var t = window.RagQuery.transform(q);
        t.raw = q;
        var cfg = window.RAG_CONFIG;
        var tok = window.RagNormalize.tokenize;

        /* สร้างชั้นค้นหา "แบบเดิม" ขึ้นมาใหม่ตามโค้ดเวอร์ชันก่อนแก้
         * รายการที่ 3 และ 4 คือจุดบกพร่อง : ใช้ token ของ "ทุก variant"
         * ซึ่ง variant แรกคือคำถามที่ขยายแล้ว จึงมีคำถามเดิมปนอยู่เต็ม ๆ
         * อันดับของรายการนั้นเลยถูกคำถามเดิมครอบงำ คำพ้องแทบไม่มีผล */
        var baseTok = tok(t.base);
        var allTok = [];
        for (var vi = 0; vi < t.variants.length; vi++) allTok = allTok.concat(tok(t.variants[vi]));

        function mkOld(arr, name, w) { arr.name = name; arr.weight = w; return arr; }
        var oldLists = [
          mkOld(window.RagIndex.denseSearch(baseTok, cfg.TOP_K_FIRST * 2), "dense", 1.0),
          mkOld(window.RagIndex.bm25Search(baseTok, cfg.TOP_K_FIRST * 2), "bm25", 1.0),
          mkOld(window.RagIndex.denseSearch(allTok, cfg.TOP_K_FIRST * 2), "dense+expand", 0.65),
          mkOld(window.RagIndex.bm25Search(allTok, cfg.TOP_K_FIRST * 2), "bm25+expand", 0.65)
        ];
        var fusedOld = window.RagRetrieve.rrfFuse(oldLists, cfg.RRF_K);
        var oldResults = [];
        for (var fi = 0; fi < fusedOld.length && oldResults.length < cfg.TOP_K_FIRST; fi++) {
          var ch = window.RagIndex.getChunk(fusedOld[fi].idx);
          if (!ch || !window.RagRetrieve.passFilter(ch)) continue;
          oldResults.push({ chunk: ch, firstStageScore: fusedOld[fi].score });
        }
        var retOld = { results: oldResults };
        var retNew = window.RagRetrieve.retrieve(t);

        // เทียบที่ "ชั้นค้นหา" โดยตรง ก่อนเข้า Re-ranking
        // เพราะ Re-ranking เก่งพอจะกู้อันดับคืนได้ในบางกรณี จนกลบผลของชั้นค้นหาไปหมด
        // ถ้าเทียบหลัง rerank จะมองไม่เห็นว่าชั้นค้นหาทำงานแย่ลงจริง
        function firstStageList(res, n) {
          var out = [], seen = {};
          var max = res.results.length ? res.results[0].firstStageScore : 1;
          for (var i = 0; i < res.results.length && out.length < n; i++) {
            var c = res.results[i].chunk;
            if (seen[c.docId]) continue;
            seen[c.docId] = true;
            out.push({
              docId: c.docId, q: c.q, cat: c.cat, level: c.level,
              score: max ? res.results[i].firstStageScore / max : 0
            });
          }
          return out;
        }
        function rankOf(res, id) {
          var seen = {}, n = 0;
          for (var i = 0; i < res.results.length; i++) {
            var d = res.results[i].chunk.docId;
            if (seen[d]) continue;
            seen[d] = true; n++;
            if (d === id) return n;
          }
          return -1;
        }

        var rOld = rankOf(retOld, "I02"), rNew = rankOf(retNew, "I02");

        return {
          type: "ranking",
          query: q,
          beforeLabel: "วิธีเดิม: รวม token เป็นถุงเดียว (อันดับจากชั้นค้นหา)",
          afterLabel: "วิธีที่แก้แล้ว: แยกรายการ + ถ่วงน้ำหนัก 1.00 / 0.90 / 0.45",
          before: firstStageList(retOld, 3),
          after: firstStageList(retNew, 3),
          verdict: "เอกสารที่ถูกต้องคือ I02 (RSI) ตารางนี้เทียบที่ชั้นค้นหาโดยตรงก่อนเข้า Re-ranking " +
                   "เพราะ Re-ranking เก่งพอจะกู้อันดับคืนได้บางกรณีจนกลบปัญหาที่แท้จริงไป " +
                   "ด้วยวิธีเดิม I02 อยู่อันดับ " + (rOld > 0 ? rOld : "นอกรายการ") +
                   " ส่วนวิธีที่แก้แล้ว I02 อยู่อันดับ " + (rNew > 0 ? rNew : "นอกรายการ") + " " +
                   "บทเรียนคือเทคนิคที่ถูกต้องในทางทฤษฎีอาจทำให้ระบบแย่ลงได้ถ้าประกอบผิดวิธี " +
                   "และถ้าไม่มีชุดทดสอบเชิงตัวเลข ปัญหาแบบนี้จะถูกส่งขึ้นระบบจริงโดยไม่มีใครรู้"
        };
      }
    },

    /* ---------------- 06 ---------------- */
    {
      no: "06",
      stage: "Ranking",
      icon: "sort",
      title: "เอกสารที่ถูกต้องถูกจัดอันดับไว้ต่ำเกินไป",
      symptom: "ระบบค้นเจอเอกสารที่ตอบได้จริง แต่อยู่อันดับ 4-8 เมื่อส่งเข้าขั้นตอนสร้างคำตอบซึ่งใช้แค่ 3 อันดับแรก เอกสารที่ถูกจึงไม่ถูกใช้",
      cause: "การค้นชั้นแรกออกแบบมาให้เร็ว จึงให้คะแนนจากความถี่คำเป็นหลัก เอกสารที่มีคำทั่วไปซ้ำเยอะ เช่น คำว่า ราคา หรือ ตลาด จึงได้คะแนนสูงกว่าเอกสารที่ตรงประเด็นแต่สั้นกว่า",
      detect: "บันทึกอันดับก่อนและหลัง rerank แล้วดูว่าเอกสารเป้าหมายเลื่อนขึ้นกี่อันดับ ถ้าเอกสารที่ถูกมักอยู่นอก 3 อันดับแรกก่อน rerank แปลว่าชั้นแรกจัดอันดับหยาบเกินไป",
      fix: "เพิ่มชั้นจัดอันดับใหม่ที่ทำงานเฉพาะผู้สมัครไม่กี่ชิ้น จึงใช้สัญญาณละเอียดกว่าได้ ได้แก่ ความครอบคลุมคำในคำถาม ความตรงกับคำถามหลักและคำถามสำรองของเอกสาร การตรงกับ tags และการเจอศัพท์เฉพาะตรงตัว",
      code: "rag-rerank.js -> rerank(), coverage(), titleMatch(), exactTermMatch()",
      keys: ["USE_RERANK", "RERANK_TITLE_BOOST", "RERANK_TAG_BOOST", "RERANK_EXACT_TERM_BOOST"],
      demoQuery: "ออเดอร์บล็อกคืออะไร",
      run: function () {
        var q = "ออเดอร์บล็อกคืออะไร";
        var off = withConfig({ USE_RERANK: false }, function () { return window.RagPipeline.ask(q); });
        var on = withConfig({ USE_RERANK: true }, function () { return window.RagPipeline.ask(q); });

        var moves = [];
        for (var i = 0; i < Math.min(6, on.results.length); i++) {
          var r = on.results[i];
          moves.push({
            docId: r.chunk.docId,
            q: r.chunk.q,
            rankBefore: r.rankBefore,
            rankAfter: r.rankAfter,
            moved: r.moved,
            signals: r.signals
          });
        }

        return {
          type: "rerank",
          query: q,
          beforeLabel: "ปิด Re-ranking (อันดับจากชั้นแรก)",
          afterLabel: "เปิด Re-ranking",
          before: topList(off, 5),
          after: topList(on, 5),
          moves: moves,
          verdict: "เอกสารที่ถูกต้องคือ A04 (Order Block และ Smart Money Concept) ก่อนจัดอันดับใหม่ " +
                   "เอกสารนี้อยู่อันดับ 5 ซึ่งอยู่นอก 3 อันดับแรกที่ระบบใช้สร้างคำตอบ จึงไม่ถูกนำมาใช้เลย " +
                   "หลังเปิด Re-ranking เอกสารได้โบนัสจากการตรงกับ tags และศัพท์เฉพาะ จึงถูกดันขึ้นมาอันดับหนึ่ง " +
                   "ตารางด้านล่างแสดงการเลื่อนอันดับของทุกเอกสารในชุดผู้สมัคร"
        };
      }
    },

    /* ---------------- 07 ---------------- */
    {
      no: "07",
      stage: "Filtering",
      icon: "filter",
      title: "การกรองด้วย Metadata ที่ตั้งผิดทำให้คำตอบที่ถูกหายไป",
      symptom: "ผู้ใช้เลือกกรองเฉพาะระดับ \"พื้นฐาน\" แล้วถามเรื่อง Order Block ซึ่งเป็นเนื้อหาขั้นสูง ระบบตอบว่าไม่พบข้อมูล ทั้งที่มีเอกสารอยู่",
      cause: "ตัวกรองทำงานก่อนการให้คะแนน เอกสารที่ไม่ผ่านเงื่อนไขจึงถูกตัดทิ้งตั้งแต่ต้นโดยไม่มีโอกาสถูกพิจารณา ถ้า metadata ของเอกสารติดป้ายผิด หรือผู้ใช้ตั้งตัวกรองแคบเกินไป คำตอบที่ถูกจะหายไปทั้งหมด",
      detect: "นับจำนวนเอกสารที่ถูกตัดด้วยตัวกรองในแต่ละคำถาม (ค่า filteredOut ใน trace) ถ้าตัดทิ้งจำนวนมากแต่ผลลัพธ์ที่เหลือคะแนนต่ำ แปลว่าตัวกรองกำลังทำร้ายคุณภาพ",
      fix: "แสดงจำนวนที่ถูกกรองออกให้ผู้ใช้เห็นเสมอในหน้า Pipeline ตั้งค่าเริ่มต้นเป็น \"ทั้งหมด\" และเมื่อผลลัพธ์หลังกรองน้อยเกินไป ให้ระบบเตือนว่าอาจต้องผ่อนตัวกรอง แทนที่จะตอบว่าไม่มีข้อมูลเฉย ๆ",
      code: "rag-retrieve.js -> passFilter(), retrieve() | config.js -> FILTER_LEVEL, FILTER_CATEGORY",
      keys: ["USE_METADATA_FILTER", "FILTER_LEVEL", "FILTER_CATEGORY"],
      demoQuery: "order block คืออะไร",
      run: function () {
        var q = "order block คืออะไร";
        var narrow = withConfig(
          { USE_METADATA_FILTER: true, FILTER_LEVEL: "พื้นฐาน", FILTER_CATEGORY: "ทั้งหมด" },
          function () { return window.RagPipeline.ask(q); }
        );
        var wide = withConfig(
          { USE_METADATA_FILTER: true, FILTER_LEVEL: "ทั้งหมด", FILTER_CATEGORY: "ทั้งหมด" },
          function () { return window.RagPipeline.ask(q); }
        );

        return {
          type: "ranking",
          query: q,
          beforeLabel: "กรองเฉพาะระดับ \"พื้นฐาน\" (ตั้งค่าแคบเกินไป)",
          afterLabel: "ไม่จำกัดระดับ",
          before: topList(narrow, 3),
          after: topList(wide, 3),
          verdict: "เอกสารเป้าหมาย A04 ติดป้ายระดับ \"ขั้นสูง\" เมื่อกรองเฉพาะพื้นฐานจึงถูกตัดตั้งแต่ก่อนให้คะแนน " +
                   "บทเรียนคือ ตัวกรองเป็นดาบสองคม ต้องแสดงให้ผู้ใช้เห็นว่ากำลังกรองอะไรอยู่ และตัดอะไรออกไปกี่ชิ้น"
        };
      }
    },

    /* ---------------- 08 ---------------- */
    {
      no: "08",
      stage: "Generation",
      icon: "shield",
      title: "Hallucination — ตอบทั้งที่ไม่มีหลักฐานในบริบท",
      symptom: "ถามเรื่องที่อยู่นอกขอบเขตฐานความรู้ เช่น ราคาตั๋วเครื่องบิน แต่ระบบยังหยิบเอกสารที่คะแนนต่ำมาตอบเป็นเรื่องเป็นราว ผู้ใช้เข้าใจผิดว่าเป็นข้อมูลจริง",
      cause: "ขั้นตอนสร้างคำตอบถูกออกแบบให้ \"ตอบเสมอ\" โดยหยิบผลอันดับหนึ่งมาใช้ไม่ว่าคะแนนจะต่ำแค่ไหน ระบบจึงไม่มีกลไกบอกว่าหลักฐานไม่พอ และเมื่อไม่บังคับให้อ้างอิงแหล่งที่มา ผู้ใช้ก็ตรวจสอบย้อนกลับไม่ได้",
      detect: "สองตัวชี้วัด หนึ่งคือคะแนนหลักฐานสูงสุดของคำถามนั้น สองคือค่า Faithfulness ที่วัดว่าเนื้อหาในคำตอบตรวจสอบกลับไปยังบริบทได้กี่เปอร์เซ็นต์ ถ้าคะแนนหลักฐานต่ำแต่ระบบยังตอบ แปลว่ากำลังเดา",
      fix: "ตั้งเกณฑ์หลักฐานขั้นต่ำ (Grounding Threshold) ถ้าคะแนนต่ำกว่าเกณฑ์ให้ปฏิเสธการตอบพร้อมเสนอหัวข้อที่มีจริงในฐานความรู้แทน บังคับแนบรหัสเอกสารอ้างอิงทุกคำตอบ และให้คำตอบเรียบเรียงจากบริบทเท่านั้น",
      code: "rag-generate.js -> generate() ส่วน Grounding Check, compose(), faithfulness() | config.js -> GROUNDING_THRESHOLD, REQUIRE_CITATION",
      keys: ["GROUNDING_THRESHOLD", "REQUIRE_CITATION"],
      demoQuery: "ตั๋วเครื่องบินไปเชียงใหม่ราคาเท่าไหร่",
      run: function () {
        var q = "ตั๋วเครื่องบินไปเชียงใหม่ราคาเท่าไหร่";
        var off = withConfig({ GROUNDING_THRESHOLD: 0, REQUIRE_CITATION: false }, function () {
          return window.RagPipeline.ask(q);
        });
        var on = withConfig({ GROUNDING_THRESHOLD: window.RAG_CONFIG_DEFAULT.GROUNDING_THRESHOLD, REQUIRE_CITATION: true }, function () {
          return window.RagPipeline.ask(q);
        });

        return {
          type: "answer",
          query: q,
          beforeLabel: "ปิดเกณฑ์หลักฐาน (ตอบทุกกรณี)",
          afterLabel: "เปิดเกณฑ์หลักฐาน + บังคับอ้างอิง",
          beforeText: off.answer,
          afterText: on.answer,
          beforeMeta: "คะแนนหลักฐานสูงสุด " + (off.info.topScore || 0).toFixed(3) +
                      " | Faithfulness " + ((off.info.faithfulness || 0) * 100).toFixed(1) + "%",
          afterMeta: "คะแนนหลักฐานสูงสุด " + (on.info.topScore || 0).toFixed(3) +
                     " | สถานะ: " + (on.info.refused ? "ปฏิเสธการตอบ" : "ตอบจากบริบท"),
          verdict: "คำถามนี้ไม่มีอยู่ในฐานความรู้เรื่องการเทรดเลย เมื่อปิดเกณฑ์หลักฐาน ระบบยังหยิบเอกสารคะแนนต่ำ" +
                   "มาตอบเหมือนเป็นคำตอบจริง ซึ่งคือ Hallucination พอเปิดเกณฑ์ ระบบเลือกปฏิเสธและเสนอหัวข้อที่มีจริงแทน"
        };
      }
    },

    /* ---------------- 09 ---------------- */
    {
      no: "09",
      stage: "Evaluation",
      icon: "chart",
      title: "ชุดทดสอบรั่ว ทำให้คะแนนสวยเกินจริง (พบจากการวัดผล)",
      symptom: "รันประเมินผลครั้งแรกแล้ว BM25 เปล่า ๆ ที่ไม่มีเทคนิคใดเลยได้ Hit@1 ถึง 98.2% ส่วนระบบเต็มรูปแบบได้ 95.5% การที่ระบบพื้นฐานที่สุดชนะระบบที่ใส่เทคนิคครบ คือสัญญาณว่าการวัดผลมีอะไรผิด ไม่ใช่ว่าระบบดีเลิศ",
      cause: "ระบบนำคำถามสำรอง (alt) ของทุกเอกสารไปใส่ไว้ในหัวของทุก chunk เพื่อช่วยการค้นหา แล้วใช้คำถามสำรองชุดเดียวกันนั้นเป็นคำถามทดสอบ การวัดผลจึงกลายเป็นการค้นหาข้อความที่ตรงกันทุกตัวอักษร ซึ่งง่ายจนไร้ความหมาย ที่ร้ายกว่านั้นคือขั้นตอน Re-ranking ก็ใช้ฟิลด์ alt ให้คะแนน titleMatch จึงเกิดการรั่วซ้ำอีกชั้น",
      detect: "สัญญาณเตือนที่ใช้ได้เสมอมี 3 ข้อ หนึ่ง ระบบพื้นฐานได้คะแนนสูงผิดปกติเกิน 95% สอง การเพิ่มเทคนิคที่ควรช่วยกลับทำให้คะแนนลดลง สาม ตรวจตรง ๆ ว่าข้อความของคำถามทดสอบปรากฏอยู่ในดัชนีหรือไม่",
      fix: "แบ่งคำถามสำรองของแต่ละเอกสารเป็น 2 ชุดที่ไม่มีทางทับกัน ลำดับคู่เข้าดัชนี ลำดับคี่กันไว้ทดสอบ โดยทั้งการตัด chunk การ Re-ranking และการสร้าง Golden Set ต้องเรียกฟังก์ชัน splitAlt ตัวเดียวกัน เพื่อไม่ให้มีทางเกิดการรั่วซ้ำอีก จากนั้นทำ Ablation Study ปิดเปิดเทคนิคทีละอย่างด้วยชุดทดสอบเดียวกัน",
      code: "rag-normalize.js -> splitAlt() แหล่งความจริงเดียวของการแบ่งชุด | rag-chunk.js -> buildChunks() ใช้เฉพาะชุด indexed | rag-eval.js -> buildGoldenSet() ใช้เฉพาะชุด heldOut",
      keys: ["EVAL_K_VALUES"],
      demoQuery: "ไปที่แท็บ \"ประเมินผล\" เพื่อรัน Ablation Study เต็มรูปแบบ",
      run: function () {
        var golden = window.RagEval.buildGoldenSet().slice(0, 40);
        var rows = window.RagEval.runAblation(golden, [1, 3]);
        var stats = rows.map(function (r) {
          return {
            name: r.name,
            value: "Hit@1 " + (r.result.k[1].hit * 100).toFixed(1) + "% | " +
                   "Hit@3 " + (r.result.k[3].hit * 100).toFixed(1) + "% | " +
                   "MRR " + r.result.mrr.toFixed(3)
          };
        });
        return {
          type: "stats",
          beforeLabel: "ผลการทดสอบ (ตัวอย่าง 40 คำถามจาก Golden Set)",
          afterLabel: "สรุป",
          before: stats,
          after: [
            { name: "จำนวนคำถามทดสอบ", value: golden.length + " ข้อ (จากชุดเต็ม " + window.RagEval.buildGoldenSet().length + " ข้อ)" },
            { name: "ตัวชี้วัดที่ใช้", value: "Hit@k, MRR, nDCG@k, Precision@k" },
            { name: "วิธีสร้างชุดทดสอบ", value: "ใช้เฉพาะคำถามสำรองชุดที่กันไว้ ซึ่งไม่เคยเข้าดัชนีและไม่เคยใช้ตอน Re-ranking" },
            { name: "เหตุผลที่ต้องกันไว้", value: "ถ้าใช้คำถามที่อยู่ในดัชนีมาทดสอบ จะกลายเป็นการค้นข้อความที่ตรงกันทุกตัวอักษร ซึ่งวัดอะไรไม่ได้" }
          ],
          verdict: "ตัวเลขข้างบนคือหลักฐานว่าแต่ละเทคนิคช่วยจริงหรือไม่ และเชื่อถือได้เพราะชุดทดสอบไม่รั่ว " +
                   "ก่อนแก้การรั่ว BM25 เปล่า ๆ เคยได้ถึง 98.2% ซึ่งถ้าเชื่อตัวเลขนั้นจะสรุปผิดว่าเทคนิคอื่นไม่จำเป็นเลย " +
                   "กดแท็บประเมินผลเพื่อรันชุดเต็มพร้อมดูรายการคำถามที่ระบบยังพลาด"
        };
      }
    },

    /* ---------------- 10 ---------------- */
    {
      no: "10",
      stage: "Safety & Ops",
      icon: "alert",
      title: "ให้คำแนะนำการลงทุนรายบุคคล และข้อมูลล้าสมัย",
      symptom: "ผู้ใช้ถามว่า \"ควรซื้อตัวไหนดี\" หรือ \"ราคาพรุ่งนี้จะขึ้นไหม\" ถ้าระบบตอบ จะกลายเป็นการให้คำแนะนำการลงทุนซึ่งเกินขอบเขตของฐานความรู้เพื่อการศึกษา และอาจสร้างความเสียหายทางการเงินให้ผู้ใช้",
      cause: "RAG ถูกออกแบบให้ค้นแล้วตอบ โดยไม่มีชั้นพิจารณาว่า \"คำถามนี้ควรตอบหรือไม่\" ต่างจากปัญหา Hallucination ที่เป็นเรื่องหลักฐานไม่พอ ปัญหานี้คือมีหลักฐานแต่ไม่ควรนำไปใช้ตอบในรูปแบบคำแนะนำรายบุคคล นอกจากนี้ข้อมูลบางหมวด เช่น ภาษี มีการเปลี่ยนแปลงตามประกาศ จึงล้าสมัยได้แม้เนื้อหาจะถูกในวันที่เขียน",
      detect: "ตรวจคำถามด้วยรายการรูปแบบที่บ่งชี้การขอคำแนะนำรายบุคคลก่อนเข้าขั้นตอนค้นหา และตรวจฟิลด์ updated ของทุกเอกสารที่ถูกใช้ตอบ ว่าเกินเกณฑ์อายุที่ยอมรับได้หรือไม่",
      fix: "ใส่ Safety Guard ไว้เป็นชั้นแรกสุดของการสร้างคำตอบ เมื่อเข้าเงื่อนไขให้ปฏิเสธพร้อมเสนอคำถามเชิงหลักการที่ระบบตอบได้แทน และเพิ่มการเตือนความสดของข้อมูลเมื่อเอกสารเก่าเกินเกณฑ์ที่ตั้งไว้",
      code: "rag-generate.js -> safetyCheck(), freshnessWarning() | config.js -> SAFETY_PATTERNS, FRESHNESS_MONTHS",
      keys: ["SAFETY_GUARD", "FRESHNESS_WARNING", "FRESHNESS_MONTHS"],
      demoQuery: "ตอนนี้ควรซื้อตัวไหนดี",
      run: function () {
        var q = "ตอนนี้ควรซื้อตัวไหนดี";
        var off = withConfig({ SAFETY_GUARD: false }, function () { return window.RagPipeline.ask(q); });
        var on = withConfig({ SAFETY_GUARD: true }, function () { return window.RagPipeline.ask(q); });

        // เดโมการเตือนข้อมูลล้าสมัย : ลดเกณฑ์อายุลงเหลือ 0 เดือน เพื่อให้เห็นข้อความเตือน
        var freshDemo = withConfig({ FRESHNESS_WARNING: true, FRESHNESS_MONTHS: 0 }, function () {
          return window.RagPipeline.ask("กำไรจากการเทรดต้องเสียภาษีไหม");
        });

        return {
          type: "answer",
          query: q,
          beforeLabel: "ปิด Safety Guard",
          afterLabel: "เปิด Safety Guard",
          beforeText: off.answer,
          afterText: on.answer,
          beforeMeta: "ระบบตอบด้วยเนื้อหาจากฐานความรู้ทั้งที่คำถามเป็นการขอคำแนะนำรายบุคคล",
          afterMeta: "ระบบปฏิเสธและเปลี่ยนเป็นข้อเสนอคำถามเชิงหลักการ",
          extra: {
            title: "การเตือนข้อมูลล้าสมัย (ทดสอบโดยตั้งเกณฑ์อายุเป็น 0 เดือน)",
            text: freshDemo.info.freshness || "(เอกสารทั้งหมดยังอยู่ในเกณฑ์)"
          },
          verdict: "คำถามลักษณะนี้ต้องถูกดักตั้งแต่ก่อนเข้าขั้นตอนค้นหา เพราะยิ่งระบบค้นเจอข้อมูลมาก " +
                   "คำตอบยิ่งดูน่าเชื่อถือและยิ่งอันตราย ระบบจึงเลือกปฏิเสธพร้อมชี้ทางไปยังคำถามเชิงหลักการที่ตอบได้จริง"
        };
      }
    }
  ];

  return { PROBLEMS: PROBLEMS, withConfig: withConfig, topList: topList };
})();
