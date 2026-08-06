/*
 * script.js — ตัวควบคุมหน้าจอแชท (LAB 2 · ธีม Gemini)
 * เชื่อมช่องพิมพ์ของผู้ใช้เข้ากับ Retriever (retrieval-based QA)
 */

(function () {
  // ค่าคะแนนขั้นต่ำที่ยอมรับว่า "เจอคำตอบ" (ต่ำกว่านี้ถือว่าไม่พบในฐานความรู้)
  const SCORE_THRESHOLD = 0.12;

  const welcome = document.getElementById("welcome");
  const chat = document.getElementById("chat");
  const messages = document.getElementById("messages");
  const input = document.getElementById("inputBox");
  const sendBtn = document.getElementById("sendBtn");

  let started = false;

  // ---- สลับจากหน้าต้อนรับ -> หน้าแชท ----
  function enterChatMode() {
    if (started) return;
    started = true;
    welcome.classList.add("hidden");
    chat.classList.remove("hidden");
  }

  // ---- สร้างข้อความของผู้ใช้ (ฟองสีฟ้าทางขวา) ----
  function addUserMessage(text) {
    const row = document.createElement("div");
    row.className = "row user";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    row.appendChild(bubble);
    messages.appendChild(row);
    scrollToBottom();
  }

  // ---- สร้างคำตอบของบอท (ไอคอน Gemini + ข้อความเต็มความกว้าง) ----
  function addBotMessage(text, meta) {
    const row = document.createElement("div");
    row.className = "row bot";

    const gem = document.createElement("div");
    gem.className = "gem";
    gem.textContent = "✦";

    const answer = document.createElement("div");
    answer.className = "answer";
    answer.textContent = text;

    if (meta) {
      const m = document.createElement("span");
      m.className = "meta";
      m.textContent = meta;
      answer.appendChild(m);
    }

    row.appendChild(gem);
    row.appendChild(answer);
    messages.appendChild(row);
    scrollToBottom();
  }

  // ---- แสดงจุดกำลังพิมพ์ ----
  function addTyping() {
    const row = document.createElement("div");
    row.className = "row bot";
    row.innerHTML =
      '<div class="gem">✦</div>' +
      '<div class="answer"><div class="typing"><span></span><span></span><span></span></div></div>';
    messages.appendChild(row);
    scrollToBottom();
    return row;
  }

  function scrollToBottom() {
    chat.scrollTop = chat.scrollHeight;
  }

  // ---- ตอบคำถามด้วยระบบ retrieval ----
  function answer(query) {
    const results = Retriever.retrieve(query, 1);
    const best = results[0];

    if (!best || best.score < SCORE_THRESHOLD) {
      return {
        text:
          "ขออภัยครับ ผมยังไม่มีข้อมูลเรื่องนี้ในฐานความรู้การบริหารเงิน ✦\n" +
          "ลองถามเรื่องอื่น เช่น การออม งบประมาณ 50/30/20 เงินสำรองฉุกเฉิน การลงทุน กองทุนรวม หนี้สิน ภาษี หรือการวางแผนเกษียณดูนะครับ",
        meta: null,
      };
    }

    return {
      text: best.answer,
      meta: "หมวด: " + best.category + " • ความเกี่ยวข้อง " + Math.round(best.score * 100) + "%",
    };
  }

  // ---- จัดการเมื่อผู้ใช้ส่งคำถาม ----
  function handleSend(query) {
    query = (query || "").trim();
    if (!query) return;

    enterChatMode();
    addUserMessage(query);

    const typing = addTyping();

    // หน่วงเล็กน้อยให้เหมือนบอทกำลังคิด
    setTimeout(function () {
      typing.remove();
      const res = answer(query);
      addBotMessage(res.text, res.meta);
    }, 450);
  }

  // ---- ผูกอีเวนต์ ----
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      const val = input.value;
      input.value = "";
      handleSend(val);
    }
  });

  sendBtn.addEventListener("click", function () {
    const val = input.value;
    input.value = "";
    handleSend(val);
    input.focus();
  });

  // ---- การ์ดตัวอย่างคำถาม ----
  document.querySelectorAll(".card").forEach(function (card) {
    card.addEventListener("click", function () {
      const t = card.querySelector(".card-text");
      handleSend(t ? t.textContent : card.textContent);
    });
  });

  // ---- ปุ่มไมค์: ใช้ Web Speech API ถ้าเบราว์เซอร์รองรับ ----
  (function setupVoice() {
    const btn = document.getElementById("micBtn");
    if (!btn) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    btn.addEventListener("click", function () {
      if (!SR) {
        alert("เบราว์เซอร์นี้ยังไม่รองรับการพูด ลองพิมพ์คำถามแทนได้เลยครับ");
        return;
      }
      const rec = new SR();
      rec.lang = "th-TH";
      rec.interimResults = false;
      rec.onresult = function (ev) {
        handleSend(ev.results[0][0].transcript);
      };
      rec.start();
    });
  })();

  // โฟกัสช่องพิมพ์เมื่อเปิดหน้า
  window.addEventListener("load", function () {
    input.focus();
  });
})();
