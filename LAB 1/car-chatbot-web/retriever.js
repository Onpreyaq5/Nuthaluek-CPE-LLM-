/*
 * Retriever (เวอร์ชัน JavaScript)
 * ดัดแปลงหลักการจาก DL-03 RAG-Project/src/retriever.py
 *
 * เดิม: query -> embedding -> cosine similarity บน FAISS -> top_k
 * เวอร์ชันนี้: query -> character n-gram vector -> cosine similarity -> top_k
 *   (ทำงานฝั่ง browser ล้วน ไม่ต้องมีเซิร์ฟเวอร์หรือโมเดล)
 */

const Retriever = (function () {
  // --- เตรียมข้อความ: ตัดช่องว่าง/อักขระพิเศษ ให้เหลือแต่ตัวอักษรและตัวเลข ---
  function normalize(text) {
    return (text || "")
      .toLowerCase()
      .replace(/[^฀-๿a-z0-9]/g, ""); // เก็บอักษรไทย อังกฤษ และตัวเลข
  }

  // --- สร้าง character n-gram (รองรับภาษาไทยที่ไม่มีการเว้นวรรคระหว่างคำ) ---
  function ngrams(text, n) {
    const t = normalize(text);
    const grams = [];
    if (t.length < n) {
      if (t.length > 0) grams.push(t);
      return grams;
    }
    for (let i = 0; i <= t.length - n; i++) {
      grams.push(t.slice(i, i + n));
    }
    return grams;
  }

  // --- แปลงข้อความเป็นเวกเตอร์ความถี่ของ bi-gram + tri-gram (คล้าย embedding) ---
  function vectorize(text) {
    const vec = {};
    for (const g of ngrams(text, 2)) vec[g] = (vec[g] || 0) + 1;
    for (const g of ngrams(text, 3)) vec[g] = (vec[g] || 0) + 1;
    return vec;
  }

  // --- cosine similarity ระหว่างสองเวกเตอร์ ---
  function cosine(a, b) {
    let dot = 0;
    let na = 0;
    let nb = 0;
    for (const k in a) {
      na += a[k] * a[k];
      if (b[k]) dot += a[k] * b[k];
    }
    for (const k in b) nb += b[k] * b[k];
    if (na === 0 || nb === 0) return 0;
    return dot / (Math.sqrt(na) * Math.sqrt(nb));
  }

  // --- pre-compute เวกเตอร์ของฐานความรู้ไว้ล่วงหน้า (เหมือน vector database) ---
  const store = CAR_KNOWLEDGE.map(function (item) {
    // ให้น้ำหนักที่ตัว "คำถาม" มากที่สุด แล้วเสริมด้วยคำในคำตอบ/หมวด
    const indexedText = item.question + " " + item.question + " " + item.category + " " + item.answer;
    return {
      item: item,
      vector: vectorize(indexedText),
      questionVector: vectorize(item.question),
    };
  });

  /**
   * ค้นหาคำตอบที่เกี่ยวข้องที่สุด
   * @param {string} query คำถามจากผู้ใช้
   * @param {number} topK จำนวนผลลัพธ์
   * @returns {Array<{score:number, category:string, question:string, answer:string}>}
   */
  function retrieve(query, topK) {
    topK = topK || 1;
    const qVec = vectorize(query);

    const scored = store.map(function (entry) {
      // รวมคะแนน: ความคล้ายรวม (0.6) + ความคล้ายเฉพาะคำถาม (0.4)
      const scoreAll = cosine(qVec, entry.vector);
      const scoreQ = cosine(qVec, entry.questionVector);
      const score = 0.6 * scoreAll + 0.4 * scoreQ;
      return {
        score: score,
        category: entry.item.category,
        question: entry.item.question,
        answer: entry.item.answer,
      };
    });

    scored.sort(function (a, b) {
      return b.score - a.score;
    });

    return scored.slice(0, topK);
  }

  return { retrieve: retrieve };
})();
