/* =============================================================
 *  rag-chunk.js — Stage 2 : Chunking
 *
 *  แก้ปัญหา 02 (Chunk ใหญ่/เล็กเกินไป และบริบทขาดตรงรอยต่อ)
 *  หลักการ 2 ชั้น
 *   ชั้นที่ 1 : ตัดตามโครงสร้างก่อน (บรรทัด / หัวข้อย่อย) -> ความหมายไม่ขาดกลางประโยค
 *   ชั้นที่ 2 : ถ้าชิ้นไหนยังยาวเกิน CHUNK_SIZE ค่อยตัดตามขนาด + ใส่ OVERLAP
 * ============================================================= */

window.RagChunk = (function () {

  /* ตัดข้อความยาวเป็นช่วง ๆ ตามขนาด พร้อมส่วนซ้อนทับ */
  function splitBySize(text, size, overlap) {
    var out = [];
    if (size <= 0) return [text];
    var step = Math.max(1, size - overlap);
    for (var i = 0; i < text.length; i += step) {
      var piece = text.slice(i, i + size);
      if (piece.trim().length > 0) out.push(piece);
      if (i + size >= text.length) break;
    }
    return out;
  }

  /* ตัดตามโครงสร้างก่อน แล้วรวมบรรทัดสั้น ๆ ให้ได้ขนาดใกล้ CHUNK_SIZE */
  function splitByStructure(text, size) {
    var lines = text.split(/\n+/);
    var groups = [];
    var buf = "";

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim();
      if (!line) continue;

      // ถ้าบรรทัดเดียวยาวเกินขนาดที่กำหนด ให้ปล่อยเป็นชิ้นของตัวเอง
      if (line.length >= size) {
        if (buf) { groups.push(buf); buf = ""; }
        groups.push(line);
        continue;
      }
      if ((buf + "\n" + line).length > size) {
        groups.push(buf);
        buf = line;
      } else {
        buf = buf ? (buf + "\n" + line) : line;
      }
    }
    if (buf) groups.push(buf);
    return groups;
  }

  /* ---------- ฟังก์ชันหลัก : เอกสาร -> รายการ chunk ---------- */
  function buildChunks(docs) {
    var cfg = window.RAG_CONFIG;
    var chunks = [];

    for (var i = 0; i < docs.length; i++) {
      var d = docs[i];

      // นำคำถาม+คำถามสำรอง มาไว้หัว chunk ทุกชิ้น
      // เพื่อให้ทุกชิ้นยังรู้ว่า "กำลังพูดเรื่องอะไร" ไม่ใช่ลอยมาเป็นข้อความเปล่า
      //
      // สำคัญ : ใช้เฉพาะคำถามสำรอง "ชุดที่กำหนดให้เข้าดัชนี" เท่านั้น
      // อีกชุดถูกกันไว้เป็นชุดทดสอบ ถ้าเอาเข้าดัชนีด้วยจะกลายเป็นชุดทดสอบรั่ว
      var altIndexed = window.RagNormalize.splitAlt(d.alt).indexed;
      var header = d.q + (altIndexed.length ? " | " + altIndexed.join(" | ") : "");
      var body = d.a;

      var pieces;
      if (cfg.CHUNK_STRUCTURE_AWARE) {
        pieces = splitByStructure(body, cfg.CHUNK_SIZE);
        // ชิ้นไหนยังยาวเกิน ให้ตัดซ้ำตามขนาด
        var expanded = [];
        for (var p = 0; p < pieces.length; p++) {
          if (pieces[p].length > cfg.CHUNK_SIZE) {
            expanded = expanded.concat(
              splitBySize(pieces[p], cfg.CHUNK_SIZE, cfg.CHUNK_OVERLAP)
            );
          } else {
            expanded.push(pieces[p]);
          }
        }
        pieces = expanded;
      } else {
        pieces = splitBySize(body, cfg.CHUNK_SIZE, cfg.CHUNK_OVERLAP);
      }

      for (var k = 0; k < pieces.length; k++) {
        chunks.push({
          chunkId: d.id + "#" + (k + 1),
          docId: d.id,
          part: k + 1,
          totalParts: pieces.length,
          cat: d.cat,
          level: d.level,
          tags: d.tags || [],
          q: d.q,
          // เก็บเฉพาะชุดที่เข้าดัชนี เพราะขั้นตอน Re-ranking ใช้ฟิลด์นี้ให้คะแนนด้วย
          // ถ้าใส่ชุดทดสอบเข้าไปจะรั่วที่ชั้นจัดอันดับอีกทาง
          alt: altIndexed,
          updated: d.updated || "",
          // ข้อความที่เอาไปทำดัชนี = หัวเรื่อง + เนื้อหาส่วนนี้
          text: header + "\n" + pieces[k],
          body: pieces[k],
          fullAnswer: d.a
        });
      }
    }
    return chunks;
  }

  /* สถิติของการ chunk ใช้แสดงในหน้า Pipeline / Problem Lab */
  function stats(chunks) {
    if (!chunks.length) return { count: 0, avg: 0, min: 0, max: 0 };
    var lens = chunks.map(function (c) { return c.body.length; });
    var sum = lens.reduce(function (a, b) { return a + b; }, 0);
    return {
      count: chunks.length,
      avg: Math.round(sum / chunks.length),
      min: Math.min.apply(null, lens),
      max: Math.max.apply(null, lens)
    };
  }

  return { buildChunks: buildChunks, stats: stats, splitBySize: splitBySize };
})();
