/*
 * script.js — ตัวควบคุมหน้าจอแชท
 * เชื่อมช่องพิมพ์ของผู้ใช้เข้ากับ Retriever (retrieval-based QA)
 */

(function () {
  // ค่าคะแนนขั้นต่ำที่ยอมรับว่า "เจอคำตอบ" (ต่ำกว่านี้ถือว่าไม่พบในฐานความรู้)
  const SCORE_THRESHOLD = 0.12;

  const welcome = document.getElementById("welcome");
  const chat = document.getElementById("chat");
  const dock = document.getElementById("dock");
  const messages = document.getElementById("messages");

  const inputTop = document.getElementById("inputTop");
  const inputBottom = document.getElementById("inputBottom");

  let started = false;

  // ---- สลับจากหน้าต้อนรับ -> หน้าแชท ----
  function enterChatMode() {
    if (started) return;
    started = true;
    welcome.classList.add("hidden");
    chat.classList.remove("hidden");
    dock.classList.remove("hidden");
  }

  // ---- สร้างบับเบิลข้อความ ----
  function addMessage(role, text, meta) {
    const row = document.createElement("div");
    row.className = "row " + role;

    const avatar = document.createElement("div");
    avatar.className = "avatar " + (role === "bot" ? "bot" : "user");
    avatar.textContent = role === "bot" ? "🚗" : "🙂";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    if (meta) {
      const m = document.createElement("span");
      m.className = "meta";
      m.textContent = meta;
      bubble.appendChild(m);
    }

    // ผู้ใช้อยู่ขวา: ข้อความก่อน avatar / บอทอยู่ซ้าย: avatar ก่อนข้อความ
    if (role === "user") {
      row.appendChild(bubble);
      row.appendChild(avatar);
    } else {
      row.appendChild(avatar);
      row.appendChild(bubble);
    }

    messages.appendChild(row);
    scrollToBottom();
    return bubble;
  }

  // ---- แสดงจุดกำลังพิมพ์ ----
  function addTyping() {
    const row = document.createElement("div");
    row.className = "row bot";
    row.innerHTML =
      '<div class="avatar bot">🚗</div>' +
      '<div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
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
          "ขออภัยครับ ผมยังไม่มีข้อมูลเรื่องนี้ในฐานความรู้เรื่องรถยนต์ 🚗\n" +
          "ลองถามเรื่องอื่น เช่น น้ำมันเครื่อง ยาง แบตเตอรี่ เบรก เกียร์ รถ EV หรือการขับขี่ปลอดภัยดูนะครับ",
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
    addMessage("user", query);

    const typing = addTyping();

    // หน่วงเล็กน้อยให้เหมือนบอทกำลังคิด
    setTimeout(function () {
      typing.remove();
      const res = answer(query);
      addMessage("bot", res.text, res.meta);
    }, 450);
  }

  // ---- ผูกอีเวนต์กับช่องพิมพ์ทั้งสอง ----
  function bindInput(input) {
    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        const val = input.value;
        input.value = "";
        handleSend(val);
        if (inputBottom) inputBottom.focus();
      }
    });
  }

  bindInput(inputTop);
  bindInput(inputBottom);

  // ---- ปุ่มตัวอย่างคำถาม ----
  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      handleSend(chip.textContent);
    });
  });

  // ---- ปุ่มไมค์ / Voice: ใช้ Web Speech API ถ้าเบราว์เซอร์รองรับ ----
  function setupVoice(micId) {
    const btn = document.getElementById(micId);
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
  }

  setupVoice("micTop");
  setupVoice("micBottom");
  setupVoice("voiceTop");
  setupVoice("voiceBottom");

  // โฟกัสช่องพิมพ์เมื่อเปิดหน้า
  window.addEventListener("load", function () {
    inputTop.focus();
  });
})();
