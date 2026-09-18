/* =============================================================
 *  app.js — ตัวควบคุมหน้าจอทั้งหมด เชื่อม UI เข้ากับ RAG Pipeline
 * ============================================================= */

(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function nl2br(s) { return esc(s).replace(/\n/g, "<br>"); }
  function pct(x) { return (x * 100).toFixed(1) + "%"; }

  /* =========================================================
   *  ตัวช่วยด้านการเคลื่อนไหว (Motion helpers)
   *
   *  ทั้งหมดเช็ค REDUCED ก่อนเสมอ ถ้าผู้ใช้ตั้งค่าลดการเคลื่อนไหวไว้
   *  จะข้ามไปแสดงผลลัพธ์สุดท้ายทันที ไม่ใช่แค่เล่นให้เร็วขึ้น
   * ========================================================= */
  var REDUCED = !!(window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches);

  /* นับเลขไต่ขึ้นจนถึงค่าจริง ใช้กับสถิติและตัวชี้วัด
   * ประโยชน์ไม่ใช่แค่สวย แต่ทำให้สายตาจับได้ว่าตัวเลขไหนเพิ่งเปลี่ยน */
  function countUp(el, to, fmt, dur) {
    if (!el) return;
    if (REDUCED) { el.textContent = fmt(to); return; }
    dur = dur || 850;
    var start = null;
    el.classList.add("counting");
    function step(ts) {
      if (start === null) start = ts;
      var p = Math.min(1, (ts - start) / dur);
      var eased = 1 - Math.pow(1 - p, 3);     // easeOutCubic: เร็วตอนต้น ช้าตอนจบ
      el.textContent = fmt(to * eased);
      if (p < 1) requestAnimationFrame(step);
      else { el.textContent = fmt(to); el.classList.remove("counting"); }
    }
    requestAnimationFrame(step);
  }

  var fmtInt = function (v) { return Math.round(v).toLocaleString(); };
  function fmtFixed(d, suffix) {
    return function (v) { return v.toFixed(d) + (suffix || ""); };
  }

  /* ใส่ลำดับให้แต่ละชิ้น เพื่อให้ CSS หน่วงเวลาไล่เข้าทีละชิ้นได้ */
  function setStagger(nodes) {
    for (var i = 0; i < nodes.length; i++) nodes[i].style.setProperty("--i", i);
  }

  /* เตรียมแผนภาพ SVG ให้พร้อมทำแอนิเมชัน
   * ต้องวัดความยาวเส้นจริงด้วย getTotalLength() เพราะ stroke-dasharray
   * ต้องรู้ความยาวที่แน่นอน ถึงจะซ่อนเส้นได้สนิทก่อนเริ่มวาด
   * ค่าที่เดาไว้ตายตัวจะทำให้เส้นสั้นโผล่มาก่อน หรือเส้นยาววาดไม่จบ */
  function prepareSvg(host, edgeSel, nodeSel) {
    if (!host) return;
    var edges = host.querySelectorAll(edgeSel);
    for (var i = 0; i < edges.length; i++) {
      var len = 300;
      try { len = Math.ceil(edges[i].getTotalLength()) || 300; } catch (e) { /* เบราว์เซอร์เก่า */ }
      edges[i].style.setProperty("--len", len);
      edges[i].style.setProperty("--i", i);
    }
    setStagger(host.querySelectorAll(nodeSel));
  }

  /* เล่นแอนิเมชันเข้าใหม่อีกครั้ง ใช้ตอนสลับแท็บ
   * ต้องสั่ง animation:none แล้วอ่าน offsetHeight เพื่อบังคับให้เบราว์เซอร์
   * คำนวณผังใหม่ ไม่งั้นการลบแล้วใส่คลาสกลับในเฟรมเดียวกันจะไม่มีผล */
  function replayIn(scope) {
    if (REDUCED || !scope) return;
    var els = scope.querySelectorAll(".stagger-in, .stage-card, .mm-node, .mm-edge, .uc-oval, .uc-actor, .uc-line, .uc-dash");
    for (var i = 0; i < els.length; i++) {
      els[i].style.animation = "none";
      void els[i].offsetHeight;
      els[i].style.animation = "";
    }
  }

  /* =========================================================
   *  เริ่มต้นระบบ
   * ========================================================= */
  function init() {
    loadSavedConfig();

    var build = window.RagPipeline.buildIndex();
    showStats(build);

    bindTabs();
    bindChat();
    bindFilters();
    bindInspector();
    renderSuggestions();
    renderProblems();
    renderUseCases();
    renderMindmap("system");
    bindMindmapSwitch();
    bindEvaluation();
    renderSettings();
    populateCategories();
  }

  /* =========================================================
   *  แท็บ
   * ========================================================= */
  function bindTabs() {
    var tabs = document.querySelectorAll(".tab");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].addEventListener("click", function () {
        var name = this.getAttribute("data-tab");
        var all = document.querySelectorAll(".tab");
        for (var j = 0; j < all.length; j++) all[j].classList.remove("active");
        this.classList.add("active");
        var panels = document.querySelectorAll(".panel");
        for (var k = 0; k < panels.length; k++) panels[k].classList.remove("active");
        var panel = $("panel-" + name);
        panel.classList.add("active");
        // เล่นแอนิเมชันเข้าใหม่ทุกครั้งที่สลับมา เพื่อให้รู้สึกว่าเป็นการ "เปลี่ยนหน้า"
        // ไม่ใช่แค่เนื้อหาเปลี่ยนไปเฉย ๆ
        replayIn(panel);
        window.scrollTo({ top: 0, behavior: REDUCED ? "auto" : "smooth" });
      });
    }
  }

  /* =========================================================
   *  หน้าถาม-ตอบ
   * ========================================================= */
  var SUGGESTIONS = [
    { title: "อ่านสัญญาณตลาด", text: "RSI ใช้ยังไง", icon: "chart" },
    { title: "วางแผนความเสี่ยง", text: "คำนวณขนาดสถานะอย่างไร", icon: "shield" },
    { title: "เรียนรู้เทคนิคขั้นสูง", text: "Order Block คืออะไร", icon: "layers" }
  ];
  function renderSuggestions() {
    var host = $("suggestRow");
    host.innerHTML = "";
    SUGGESTIONS.forEach(function (item) {
      var button = document.createElement("button");
      button.className = "suggest";
      button.innerHTML = window.TradeIcons.svg(item.icon) + '<span><strong>' + esc(item.title) + '</strong><small>' + esc(item.text) + '</small></span>' + window.TradeIcons.svg("diagonal");
      button.addEventListener("click", function () {
        $("userInput").value = item.text;
        handleAsk();
      });
      host.appendChild(button);
    });
  }

  function bindChat() {
    $("sendBtn").addEventListener("click", handleAsk);
    $("userInput").addEventListener("keydown", function (e) {
      if (e.key === "Enter") handleAsk();
    });
  }

  function addMessage(who, html, cls) {
    var box = $("chatBox");
    var wrap = document.createElement("div");
    wrap.className = "msg " + who + (cls ? " " + cls : "");
    var icon = window.TradeIcons.svg(who === "user" ? "user" : "brand");
    wrap.innerHTML =
      '<div class="msg-avatar">' + icon + '</div>' +
      '<div class="msg-body"><div class="msg-name">' + (who === "user" ? "คุณ" : "TradeRAG") + '</div>' +
      html + '</div>';
    box.appendChild(wrap);
    box.scrollTop = box.scrollHeight;
    return wrap;
  }

  function handleAsk() {
    var input = $("userInput");
    var q = input.value.trim();
    if (!q || $("sendBtn").disabled) return;
    $("panel-chat").classList.add("has-conversation");

    addMessage("user", '<div class="msg-text">' + esc(q) + '</div>');
    input.value = "";
    $("sendBtn").disabled = true;

    var typing = addMessage("bot", '<div class="msg-text typing"><i></i><i></i><i></i></div>');

    setTimeout(function () {
      var res;
      try {
        res = window.RagPipeline.ask(q);
      } catch (err) {
        typing.remove();
        addMessage("bot", '<div class="msg-text">เกิดข้อผิดพลาด: ' + esc(err.message) + '</div>', "safety");
        $("sendBtn").disabled = false;
        return;
      }

      function paint(r) {
        typing.remove();
        var cls = "";
        if (r.info.reason === "safety") cls = "safety";
        else if (r.info.refused) cls = "refused";

        var chips = '<div class="msg-meta">';
        chips += '<span class="chip">ใช้เวลา ' + r.trace.totalMs + ' ms</span>';
        if (!r.info.refused) {
          var f = r.info.faithfulness;
          chips += '<span class="chip ' + (f > .75 ? "good" : (f > .5 ? "warn" : "bad")) +
                   '">Faithfulness ' + pct(f) + '</span>';
          chips += '<span class="chip good">หลักฐาน ' + r.info.topScore.toFixed(3) + '</span>';
          if (r.info.citations.length) {
            chips += '<span class="chip">อ้างอิง ' + r.info.citations.join(" ") + '</span>';
          }
        } else {
          chips += '<span class="chip ' + (r.info.reason === "safety" ? "bad" : "warn") + '">' +
                   (r.info.reason === "safety" ? "ปฏิเสธ: นอกขอบเขต" : "ปฏิเสธ: หลักฐานไม่พอ") + '</span>';
        }
        chips += '</div>';

        addMessage("bot", '<div class="msg-text">' + nl2br(r.answer) + '</div>' + chips, cls);
        renderSources(r);
        $("sendBtn").disabled = false;
      }

      if (window.RAG_CONFIG.USE_LLM && window.RAG_CONFIG.LLM_API_KEY) {
        window.RagPipeline.askWithLLM(q).then(paint);
      } else {
        paint(res);
      }
    }, 220);
  }

  function renderSources(res) {
    var host = $("sourceList");
    if (!res.results.length) {
      host.innerHTML = '<p class="empty-hint">ไม่พบเอกสารที่เกี่ยวข้อง</p>';
      return;
    }
    var html = "";
    var seen = {}, n = 0;
    for (var i = 0; i < res.results.length && n < 6; i++) {
      var r = res.results[i], c = r.chunk;
      if (seen[c.docId]) continue;
      seen[c.docId] = true; n++;
      var used = n <= window.RAG_CONFIG.TOP_K_CONTEXT && !res.info.refused;
      html += '<div class="source-item stagger-in" style="--i:' + (n - 1) +
        ';border-left-color:' + (used ? "var(--up)" : "var(--line)") + '">' +
        '<div class="sid">[' + esc(c.docId) + ']' + (used ? " · ใช้ตอบ" : "") + '</div>' +
        '<div class="sq">' + esc(c.q) + '</div>' +
        '<div class="smeta"><span>' + esc(c.cat) + '</span><span>·</span><span>' + esc(c.level) + '</span>' +
        '<span>·</span><span>คะแนน ' + r.score.toFixed(3) + '</span></div>' +
        '<div class="bar"><i style="width:' + Math.min(100, r.score * 100).toFixed(0) + '%"></i></div>' +
        '</div>';
    }
    host.innerHTML = html;
  }

  function populateCategories() {
    var cats = {}, list = [];
    var kb = window.TRADING_KB || [];
    for (var i = 0; i < kb.length; i++) {
      if (kb[i].cat && !cats[kb[i].cat]) { cats[kb[i].cat] = true; list.push(kb[i].cat); }
    }
    var sel = $("filterCategory");
    for (var j = 0; j < list.length; j++) {
      var o = document.createElement("option");
      o.textContent = list[j];
      sel.appendChild(o);
    }
  }

  function bindFilters() {
    $("filterLevel").addEventListener("change", function () {
      window.RAG_CONFIG.FILTER_LEVEL = this.value;
      saveConfig();
      updateFilterNote();
    });
    $("filterCategory").addEventListener("change", function () {
      window.RAG_CONFIG.FILTER_CATEGORY = this.value;
      saveConfig();
      updateFilterNote();
    });
    $("filterMode").addEventListener("change", function () {
      window.RAG_CONFIG.RETRIEVAL_MODE = this.value;
      saveConfig();
      updateFilterNote();
    });
  }

  function updateFilterNote() {
    var c = window.RAG_CONFIG;
    var active = [];
    if (c.FILTER_LEVEL !== "ทั้งหมด") active.push("ระดับ " + c.FILTER_LEVEL);
    if (c.FILTER_CATEGORY !== "ทั้งหมด") active.push("หมวด " + c.FILTER_CATEGORY);
    $("filterNote").textContent = active.length
      ? "กำลังกรอง: " + active.join(" และ ") + " — ถ้าถามแล้วไม่พบข้อมูล ให้ลองผ่อนตัวกรอง (ดูปัญหาข้อ 07)"
      : "ตัวกรองมีผลกับการค้นหาทันที ดูผลกระทบได้ที่แท็บตรวจสอบ Pipeline";
  }

  /* =========================================================
   *  หน้าตรวจสอบ Pipeline
   * ========================================================= */
  function bindInspector() {
    $("inspectBtn").addEventListener("click", runInspect);
    $("inspectInput").addEventListener("keydown", function (e) {
      if (e.key === "Enter") runInspect();
    });
  }

  function runInspect() {
    var q = $("inspectInput").value.trim();
    if (!q) return;
    var res = window.RagPipeline.ask(q);
    var html = "";

    for (var i = 0; i < res.trace.stages.length; i++) {
      var st = res.trace.stages[i];
      html += '<div class="stage-card" style="--i:' + i + '">' +
        '<div class="stage-head"><div class="stage-title">' +
        '<span class="stage-no">' + st.no + '</span>' + esc(st.name) + '</div>' +
        '<span class="stage-ms">' + st.ms + ' ms</span></div>' +
        '<div class="kv-grid">';
      for (var j = 0; j < st.detail.length; j++) {
        var d = st.detail[j];
        html += '<div class="kv"><div class="k">' + esc(d.name) + '</div>' +
                '<div class="v">' + esc(d.value) + '</div></div>';
      }
      html += '</div></div>';
    }

    // ตารางผลลัพธ์
    if (res.results.length) {
      html += '<div class="stage-card" style="--i:4"><div class="stage-head"><div class="stage-title">' +
        '<span class="stage-no">5</span>ผลการค้นหาหลังจัดอันดับ</div></div><div class="table-wrap"><table class="data">' +
        '<tr><th>อันดับ</th><th>รหัส</th><th>คำถามในเอกสาร</th><th>หมวด</th>' +
        '<th class="num">ก่อน</th><th class="num">หลัง</th><th class="num">คะแนน</th></tr>';
      for (var k = 0; k < Math.min(8, res.results.length); k++) {
        var r = res.results[k];
        var moved = r.moved || 0;
        html += '<tr' + (k < window.RAG_CONFIG.TOP_K_CONTEXT ? ' class="best"' : '') + '>' +
          '<td>' + (k + 1) + '</td><td>' + esc(r.chunk.docId) + '</td>' +
          '<td>' + esc(r.chunk.q) + '</td><td>' + esc(r.chunk.level) + '</td>' +
          '<td class="num">' + (r.rankBefore || "-") + '</td>' +
          '<td class="num">' + (r.rankAfter || "-") +
          (moved > 0 ? ' <span class="move-up">▲' + moved + '</span>' :
           moved < 0 ? ' <span class="move-down">▼' + (-moved) + '</span>' : '') + '</td>' +
          '<td class="num">' + r.score.toFixed(3) + '</td></tr>';
      }
      html += '</table></div></div>';
    }

    html += '<div class="answer-card"><h4>คำตอบที่ระบบสร้าง</h4><div class="txt">' +
            nl2br(res.answer) + '</div></div>';

    $("pipelineResult").innerHTML = html;
  }

  /* =========================================================
   *  หน้าปัญหา & การแก้ไข
   * ========================================================= */
  function renderProblems() {
    var host = $("problemList");
    var ps = window.RagProblems.PROBLEMS;
    var html = "";

    for (var i = 0; i < ps.length; i++) {
      var p = ps[i];
      html += '<div class="problem-card stagger-in" data-idx="' + i + '" style="--i:' + i + '">' +
        '<div class="problem-head">' +
          '<div class="problem-no">' + p.no + '</div>' +
          '<div class="problem-titlebox"><h3>' + esc(p.title) + '</h3>' +
          '<span class="problem-stage">' + esc(p.stage) + '</span></div>' +
          '<div class="problem-caret"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div>' +
        '</div>' +
        // pb-inner / pb-pad คือโครงที่ทำให้ accordion ยืด-หดได้นุ่มนวล
        // pb-inner ทำหน้าที่ตัดส่วนเกิน ส่วน pb-pad เก็บ padding ไว้
        // ถ้าใส่ padding ที่ problem-body โดยตรง จะเห็นขอบโผล่ตอนหุบ
        '<div class="problem-body"><div class="pb-inner"><div class="pb-pad">' +
          block("l-symptom", "อาการที่พบ", p.symptom) +
          block("l-cause", "สาเหตุของปัญหา", p.cause) +
          block("l-detect", "วิธีตรวจสอบ", p.detect) +
          block("l-fix", "แนวทางการแก้ไข", p.fix) +
          '<div class="pblock"><div class="plabel l-code"><i></i>ตำแหน่งใน Source Code</div>' +
            '<code class="code-ref">' + esc(p.code) + '</code>' +
            '<div class="cfg-keys">' + p.keys.map(function (k) {
              return '<span class="cfg-key">' + esc(k) + '</span>';
            }).join("") + '</div>' +
          '</div>' +
          '<div class="demo-zone">' +
            '<div class="demo-head">' +
              '<div class="demo-q">คำถามที่ใช้ทดลอง: <code>' + esc(p.demoQuery) + '</code></div>' +
              '<button class="btn primary small demo-btn" data-idx="' + i + '">ทดลองรัน</button>' +
            '</div>' +
            '<div class="demo-out" id="demoOut' + i + '"></div>' +
          '</div>' +
        '</div></div></div>' +
      '</div>';
    }
    host.innerHTML = html;

    var heads = host.querySelectorAll(".problem-head");
    for (var h = 0; h < heads.length; h++) {
      heads[h].addEventListener("click", function () {
        this.parentNode.classList.toggle("open");
      });
    }
    var btns = host.querySelectorAll(".demo-btn");
    for (var b = 0; b < btns.length; b++) {
      btns[b].addEventListener("click", function (e) {
        e.stopPropagation();
        runProblemDemo(parseInt(this.getAttribute("data-idx"), 10), this);
      });
    }
  }

  function block(cls, label, text) {
    return '<div class="pblock"><div class="plabel ' + cls + '"><i></i>' + label + '</div>' +
           '<p>' + esc(text) + '</p></div>';
  }

  function runProblemDemo(idx, btn) {
    var p = window.RagProblems.PROBLEMS[idx];
    var out = $("demoOut" + idx);
    btn.disabled = true;
    btn.textContent = "กำลังรัน...";
    out.innerHTML = '<p class="empty-hint">กำลังประมวลผล</p>';

    setTimeout(function () {
      var r;
      try {
        r = p.run();
      } catch (err) {
        out.innerHTML = '<div class="verdict">เกิดข้อผิดพลาดระหว่างทดลอง: ' + esc(err.message) + '</div>';
        btn.disabled = false; btn.textContent = "ทดลองรันอีกครั้ง";
        return;
      }
      out.innerHTML = renderDemo(r);
      btn.disabled = false;
      btn.textContent = "ทดลองรันอีกครั้ง";
    }, 60);
  }

  function rankRows(list) {
    var html = "";
    for (var i = 0; i < list.length; i++) {
      var it = list[i];
      html += '<div class="rank-row' + (i === 0 ? " hit" : "") + '" style="--i:' + i + '">' +
        '<span class="rank-n">' + (i + 1) + '</span>' +
        '<span class="rank-id">' + esc(it.docId) + '</span>' +
        '<span class="rank-q">' + esc(it.q) + '</span>' +
        '<span class="rank-score">' + it.score.toFixed(3) + '</span></div>';
    }
    return html || '<p class="empty-hint">ไม่พบผลลัพธ์</p>';
  }

  function kvRows(list) {
    var html = "";
    for (var i = 0; i < list.length; i++) {
      html += '<div class="rank-row" style="--i:' + i + '"><span class="rank-q" style="flex:0 0 auto;color:var(--text-faint)">' +
        esc(list[i].name) + '</span><span class="rank-q" style="text-align:right">' +
        esc(list[i].value) + '</span></div>';
    }
    return html;
  }

  function renderDemo(r) {
    var html = "";

    if (r.type === "ranking3") {
      html += '<div class="compare three">';
      for (var i = 0; i < r.lists.length; i++) {
        var cls = i === 2 ? "after" : "neutral";
        html += '<div class="cmp-box ' + cls + '"><div class="cmp-label">' + esc(r.labels[i]) + '</div>' +
                rankRows(r.lists[i]) + '</div>';
      }
      html += '</div>';

    } else if (r.type === "answer") {
      html += '<div class="compare">' +
        '<div class="cmp-box before"><div class="cmp-label">' + esc(r.beforeLabel) + '</div>' +
        '<div class="cmp-text">' + nl2br(r.beforeText) + '</div>' +
        '<div class="cmp-meta">' + esc(r.beforeMeta) + '</div></div>' +
        '<div class="cmp-box after"><div class="cmp-label">' + esc(r.afterLabel) + '</div>' +
        '<div class="cmp-text">' + nl2br(r.afterText) + '</div>' +
        '<div class="cmp-meta">' + esc(r.afterMeta) + '</div></div></div>';
      if (r.extra) {
        html += '<div class="verdict"><b>' + esc(r.extra.title) + '</b><br>' + esc(r.extra.text) + '</div>';
      }

    } else if (r.type === "stats") {
      html += '<div class="compare">' +
        '<div class="cmp-box before"><div class="cmp-label">' + esc(r.beforeLabel) + '</div>' +
        kvRows(r.before) + '</div>' +
        '<div class="cmp-box after"><div class="cmp-label">' + esc(r.afterLabel) + '</div>' +
        kvRows(r.after) + '</div></div>';

    } else {
      // ranking / rerank
      html += '<div class="compare">' +
        '<div class="cmp-box before"><div class="cmp-label">' + esc(r.beforeLabel) + '</div>' +
        rankRows(r.before) + '</div>' +
        '<div class="cmp-box after"><div class="cmp-label">' + esc(r.afterLabel) + '</div>' +
        rankRows(r.after) + '</div></div>';

      if (r.type === "rerank" && r.moves) {
        html += '<div class="table-wrap" style="margin-top:12px"><table class="data">' +
          '<tr><th>รหัส</th><th>คำถามในเอกสาร</th><th class="num">อันดับก่อน</th>' +
          '<th class="num">อันดับหลัง</th><th class="num">เลื่อน</th><th class="num">ตรงคำถามหลัก</th></tr>';
        for (var m = 0; m < r.moves.length; m++) {
          var mv = r.moves[m];
          html += '<tr' + (mv.rankAfter <= 3 ? ' class="best"' : '') + '><td>' + esc(mv.docId) + '</td>' +
            '<td>' + esc(mv.q) + '</td><td class="num">' + mv.rankBefore + '</td>' +
            '<td class="num">' + mv.rankAfter + '</td><td class="num">' +
            (mv.moved > 0 ? '<span class="move-up">▲' + mv.moved + '</span>' :
             mv.moved < 0 ? '<span class="move-down">▼' + (-mv.moved) + '</span>' : '–') + '</td>' +
            '<td class="num">' + (mv.signals && mv.signals.title != null ? mv.signals.title : "-") + '</td></tr>';
        }
        html += '</table></div>';
      }
    }

    if (r.verdict) html += '<div class="verdict"><b>สรุปผลการทดลอง:</b> ' + esc(r.verdict) + '</div>';
    return html;
  }

  /* =========================================================
   *  หน้าประเมินผล
   * ========================================================= */
  function bindEvaluation() {
    $("runEvalBtn").addEventListener("click", runEvaluation);
    $("runChunkBtn").addEventListener("click", runChunkStudy);
  }

  function getGolden() {
    var g = window.RagEval.buildGoldenSet();
    var size = parseInt($("evalSize").value, 10);
    return size > 0 ? g.slice(0, size) : g;
  }

  function runEvaluation() {
    var btn = $("runEvalBtn");
    btn.disabled = true;
    var golden = getGolden();
    $("evalStatus").textContent = "กำลังรัน " + golden.length + " คำถาม x 5 ชุดค่า...";
    $("evalResult").innerHTML = '<p class="empty-hint">กำลังประมวลผล</p>';

    setTimeout(function () {
      var rows = window.RagEval.runAblation(golden, [1, 3, 5, 10]);
      renderEvalResult(rows, golden.length);
      $("evalStatus").textContent = "เสร็จสิ้น";
      btn.disabled = false;
    }, 80);
  }

  function renderEvalResult(rows, total) {
    var best = rows[rows.length - 1].result;
    var baseline = rows[0].result;

    var html = '<div class="metric-cards">' +
      metricCard(pct(best.k[1].hit), "Hit@1", "คำถามที่เอกสารถูกต้องมาเป็นอันดับหนึ่ง", best.k[1].hit * 100, 1, "%") +
      metricCard(pct(best.k[3].hit), "Hit@3", "ติดใน 3 อันดับแรกที่ใช้สร้างคำตอบ", best.k[3].hit * 100, 1, "%") +
      metricCard(best.mrr.toFixed(3), "MRR", "ค่าเฉลี่ยของส่วนกลับของอันดับที่เจอ", best.mrr, 3, "") +
      metricCard(best.k[5].ndcg.toFixed(3), "nDCG@5", "ให้น้ำหนักอันดับต้นมากกว่า", best.k[5].ndcg, 3, "") +
      metricCard(total, "คำถามทดสอบ", "จากคำถามสำรองชุดที่กันไว้ ไม่เคยเข้าดัชนี", total, 0, "") +
      '</div>';

    html += '<div class="stage-card"><div class="stage-head"><div class="stage-title">' +
      '<span class="stage-no">1</span>ตารางเปรียบเทียบ (Ablation Study)</div></div>' +
      '<div class="table-wrap"><table class="data">' +
      '<tr><th>ชุดค่า</th><th>รายละเอียด</th><th class="num">Hit@1</th><th class="num">Hit@3</th>' +
      '<th class="num">Hit@5</th><th class="num">MRR</th><th class="num">nDCG@5</th></tr>';

    var bestMrr = 0;
    for (var b = 0; b < rows.length; b++) bestMrr = Math.max(bestMrr, rows[b].result.mrr);

    for (var i = 0; i < rows.length; i++) {
      var r = rows[i].result;
      html += '<tr' + (r.mrr === bestMrr ? ' class="best"' : '') + '>' +
        '<td><b>' + esc(rows[i].name) + '</b></td><td>' + esc(rows[i].note) + '</td>' +
        '<td class="num">' + pct(r.k[1].hit) + '</td>' +
        '<td class="num">' + pct(r.k[3].hit) + '</td>' +
        '<td class="num">' + pct(r.k[5].hit) + '</td>' +
        '<td class="num">' + r.mrr.toFixed(3) + '</td>' +
        '<td class="num">' + r.k[5].ndcg.toFixed(3) + '</td></tr>';
    }
    html += '</table></div></div>';

    // กราฟแท่ง Hit@3
    html += '<div class="stage-card"><div class="stage-head"><div class="stage-title">' +
      '<span class="stage-no">2</span>กราฟเปรียบเทียบ Hit@3</div></div><div class="bar-chart">';
    for (var j = 0; j < rows.length; j++) {
      var v = rows[j].result.k[3].hit;
      html += '<div class="bar-item stagger-in" style="--i:' + j + '"><span class="bname">' + esc(rows[j].name) + '</span>' +
        '<div class="bar-track"><div class="bar-fill" style="width:' + (v * 100).toFixed(1) + '%"></div></div>' +
        '<span class="bval">' + pct(v) + '</span></div>';
    }
    html += '</div></div>';

    // สรุปผล
    var gainHit = (best.k[3].hit - baseline.k[3].hit) * 100;
    var gainMrr = best.mrr - baseline.mrr;
    html += '<div class="verdict"><b>สรุป:</b> ระบบเต็มรูปแบบให้ Hit@3 สูงกว่าการใช้ BM25 อย่างเดียว ' +
      gainHit.toFixed(1) + ' จุด และ MRR สูงกว่า ' + gainMrr.toFixed(3) +
      ' ซึ่งเป็นหลักฐานเชิงตัวเลขว่าการแก้ปัญหาข้อ 03, 04, 05 และ 06 ช่วยได้จริง ' +
      'ไม่ใช่แค่ความรู้สึกจากการลองถามไม่กี่คำถาม</div>';

    // คำถามที่ยังพลาด
    if (best.failures.length) {
      html += '<div class="stage-card"><div class="stage-head"><div class="stage-title">' +
        '<span class="stage-no">3</span>คำถามที่ระบบยังหาไม่เจอ (' + best.failures.length + ' ข้อ)</div></div>' +
        '<div class="table-wrap"><table class="data"><tr><th>คำถามทดสอบ</th><th>ควรได้</th><th>ได้จริง</th></tr>';
      for (var f = 0; f < Math.min(12, best.failures.length); f++) {
        var fa = best.failures[f];
        html += '<tr><td>' + esc(fa.query) + '</td><td>' + esc(fa.expected) + '</td>' +
                '<td>' + esc(fa.got) + '</td></tr>';
      }
      html += '</table></div>' +
        '<div class="verdict" style="margin-top:10px">รายการนี้คือข้อมูลตั้งต้นสำหรับการปรับปรุงรอบถัดไป ' +
        'เช่น เพิ่มคำพ้องที่ขาดไป หรือเพิ่มคำถามสำรองให้เอกสารที่หาไม่เจอ</div></div>';
    } else {
      html += '<div class="verdict">ระบบค้นเจอเอกสารที่ถูกต้องครบทุกคำถามในชุดทดสอบนี้</div>';
    }

    $("evalResult").innerHTML = html;
    runCounters($("evalResult"));
    setStagger($("evalResult").querySelectorAll(".bar-item"));
  }

  /* การ์ดตัวชี้วัด
   * num / dec / suffix เป็นค่าสำหรับนับไต่ขึ้น ส่วน v คือข้อความสำเร็จรูป
   * ที่จะแสดงทันทีถ้าผู้ใช้ปิดแอนิเมชันไว้ จึงต้องใส่ทั้งสองอย่างเสมอ */
  function metricCard(v, l, h, num, dec, suffix) {
    var attrs = (num != null)
      ? ' data-to="' + num + '" data-dec="' + dec + '" data-suffix="' + esc(suffix || "") + '"'
      : "";
    return '<div class="metric-card stagger-in"><div class="mv"' + attrs + '>' + esc(v) + '</div>' +
           '<div class="ml">' + esc(l) + '</div><div class="mh">' + esc(h) + '</div></div>';
  }

  /* สั่งให้ทุกตัวเลขในขอบเขตที่กำหนดนับไต่ขึ้น */
  function runCounters(scope) {
    var els = scope.querySelectorAll(".mv[data-to]");
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var to = parseFloat(el.getAttribute("data-to"));
      var dec = parseInt(el.getAttribute("data-dec"), 10) || 0;
      var suffix = el.getAttribute("data-suffix") || "";
      countUp(el, to, fmtFixed(dec, suffix), 900);
    }
  }

  function runChunkStudy() {
    var btn = $("runChunkBtn");
    btn.disabled = true;
    var golden = getGolden().slice(0, 60);
    $("evalStatus").textContent = "กำลังทดสอบขนาด Chunk (ต้องสร้างดัชนีใหม่ทุกครั้ง)...";
    $("evalResult").innerHTML = '<p class="empty-hint">กำลังประมวลผล</p>';

    setTimeout(function () {
      var sizes = [
        { size: 120, overlap: 0 }, { size: 240, overlap: 40 },
        { size: 420, overlap: 80 }, { size: 800, overlap: 100 },
        { size: 2000, overlap: 0 }
      ];
      var rows = window.RagEval.runChunkStudy(golden, sizes);

      var html = '<div class="stage-card"><div class="stage-head"><div class="stage-title">' +
        '<span class="stage-no">1</span>ผลของขนาด Chunk ต่อคุณภาพการค้นหา</div></div>' +
        '<div class="table-wrap"><table class="data">' +
        '<tr><th class="num">ขนาด</th><th class="num">Overlap</th><th class="num">จำนวน Chunk</th>' +
        '<th class="num">ยาวเฉลี่ย</th><th class="num">Hit@1</th><th class="num">Hit@3</th><th class="num">MRR</th></tr>';

      var bestMrr = 0;
      for (var b = 0; b < rows.length; b++) bestMrr = Math.max(bestMrr, rows[b].result.mrr);

      for (var i = 0; i < rows.length; i++) {
        var r = rows[i];
        html += '<tr' + (r.result.mrr === bestMrr ? ' class="best"' : '') + '>' +
          '<td class="num">' + r.size + '</td><td class="num">' + r.overlap + '</td>' +
          '<td class="num">' + r.chunks + '</td><td class="num">' + r.avgLen + '</td>' +
          '<td class="num">' + pct(r.result.k[1].hit) + '</td>' +
          '<td class="num">' + pct(r.result.k[3].hit) + '</td>' +
          '<td class="num">' + r.result.mrr.toFixed(3) + '</td></tr>';
      }
      html += '</table></div></div>' +
        '<div class="verdict"><b>อ่านผลอย่างไร:</b> ขนาดเล็กเกินไปทำให้บริบทขาดและจำนวน chunk บานปลาย ' +
        'ส่วนขนาดใหญ่เกินไปทำให้เวกเตอร์หนึ่งชิ้นแทนหลายแนวคิดจนความคล้ายเจือจาง ' +
        'ค่ากลางที่มีส่วนซ้อนทับจึงมักให้ผลดีที่สุด ซึ่งเป็นเหตุผลที่ระบบนี้ตั้งค่าไว้ที่ 420 / 80 ' +
        '(ทดสอบด้วย ' + golden.length + ' คำถาม)</div>';

      $("evalResult").innerHTML = html;
      $("evalStatus").textContent = "เสร็จสิ้น";
      btn.disabled = false;
    }, 80);
  }

  /* =========================================================
   *  หน้า Mind Map
   * ========================================================= */
  function renderMindmap(key) {
    var m = window.RagMindmap.build(key);
    $("mindmapHost").innerHTML = m.svg;
    // ต้องเรียกหลังใส่ SVG ลง DOM แล้วเท่านั้น
    // เพราะ getTotalLength() จะทำงานได้ก็ต่อเมื่อ element ถูก render จริง
    prepareSvg($("mindmapHost"), ".mm-edge", ".mm-node");
    var legend = '<span style="color:var(--text)"><b>' + esc(m.title) + '</b></span>';
    for (var i = 0; i < m.branches.length; i++) {
      legend += '<span><i style="background:' + window.RagMindmap.COLORS[i % window.RagMindmap.COLORS.length] +
                '"></i>' + esc(m.branches[i].label) + '</span>';
    }
    legend += '<span style="width:100%;color:var(--text-faint)">' + esc(m.legend) + '</span>';
    $("mindmapLegend").innerHTML = legend;
  }

  function bindMindmapSwitch() {
    var segs = $("mindmapSwitch").querySelectorAll(".seg");
    for (var i = 0; i < segs.length; i++) {
      segs[i].addEventListener("click", function () {
        for (var j = 0; j < segs.length; j++) segs[j].classList.remove("active");
        this.classList.add("active");
        renderMindmap(this.getAttribute("data-map"));
      });
    }
  }

  /* =========================================================
   *  หน้า Use Case
   * ========================================================= */
  function renderUseCases() {
    $("usecaseDiagram").innerHTML = window.RagUseCases.buildDiagram();
    prepareSvg($("usecaseDiagram"), ".uc-line", ".uc-oval, .uc-actor");

    var host = $("usecaseList");
    var ucs = window.RagUseCases.USECASES;
    var html = "";

    for (var i = 0; i < ucs.length; i++) {
      var u = ucs[i];
      html += '<div class="uc-card stagger-in" style="--i:' + i + '">' +
        '<div class="uc-head"><span class="uc-id">' + esc(u.id) + '</span>' +
        '<h3>' + esc(u.name) + '</h3>' +
        '<div class="problem-caret"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg></div></div>' +
        '<div class="uc-body"><div class="uc-inner"><div class="pb-pad"><div class="uc-meta">' +
          kvBox("ผู้กระทำ (Actor)", u.actor) +
          kvBox("เป้าหมาย", u.goal) +
          kvBox("ความสำคัญ", u.priority) +
          kvBox("เงื่อนไขก่อนเริ่ม", u.pre) +
          kvBox("จุดเริ่มทำงาน (Trigger)", u.trigger) +
          kvBox("ผลลัพธ์เมื่อจบ", u.post) +
        '</div>';

      html += flowList("ลำดับการทำงานหลัก (Main Flow)", u.main, "", true);
      if (u.alt && u.alt.length) html += flowList("ทางเลือกอื่น (Alternate Flow)", u.alt, "alt", false);
      if (u.exc && u.exc.length) html += flowList("กรณีผิดปกติ (Exception Flow)", u.exc, "exc", false);
      if (u.rules && u.rules.length) html += flowList("กฎทางธุรกิจ (Business Rules)", u.rules, "", false);

      html += '<div class="pblock"><div class="plabel l-code"><i></i>ตำแหน่งใน Source Code</div>' +
              '<code class="code-ref">' + esc(u.code) + '</code></div>';
      html += '</div></div></div>';   // ปิด pb-pad, uc-inner, uc-body
      html += '</div>';               // ปิด uc-card
    }
    host.innerHTML = html;

    var heads = host.querySelectorAll(".uc-head");
    for (var h = 0; h < heads.length; h++) {
      heads[h].addEventListener("click", function () {
        this.parentNode.classList.toggle("open");
      });
    }
  }

  function kvBox(k, v) {
    return '<div class="kv"><div class="k">' + esc(k) + '</div><div class="v">' + esc(v) + '</div></div>';
  }

  function flowList(title, items, cls, ordered) {
    var tag = ordered ? "ol" : "ul";
    var html = '<div class="uc-flow"><h4 class="' + cls + '">' + esc(title) + '</h4><' + tag + '>';
    for (var i = 0; i < items.length; i++) html += '<li>' + esc(items[i]) + '</li>';
    return html + '</' + tag + '></div>';
  }

  /* =========================================================
   *  หน้าตั้งค่า
   * ========================================================= */
  var SETTING_GROUPS = [
    {
      title: "1. เตรียมข้อมูลและตัด Chunk",
      desc: "เปลี่ยนค่าในกลุ่มนี้ต้องกดสร้างดัชนีใหม่ จึงจะมีผล",
      rebuild: true,
      items: [
        { key: "NORMALIZE_TEXT", type: "bool", label: "ทำความสะอาดข้อความ", hint: "ตัวพิมพ์เล็ก ยุบช่องว่างและอักษรซ้ำ" },
        { key: "DEDUPE_DOCS", type: "bool", label: "ตัดเอกสารซ้ำ", hint: "ใช้ fingerprint เทียบ" },
        { key: "CHUNK_SIZE", type: "num", label: "ขนาด Chunk", hint: "จำนวนตัวอักษร" },
        { key: "CHUNK_OVERLAP", type: "num", label: "ส่วนซ้อนทับ", hint: "กันบริบทขาดตรงรอยต่อ" },
        { key: "CHUNK_STRUCTURE_AWARE", type: "bool", label: "ตัดตามโครงสร้างก่อน", hint: "ตัดตามบรรทัดก่อนตัดตามขนาด" },
        { key: "NGRAM_MIN", type: "num", label: "n-gram ต่ำสุด", hint: "สำหรับภาษาไทย" },
        { key: "NGRAM_MAX", type: "num", label: "n-gram สูงสุด", hint: "ยิ่งสูงยิ่งละเอียดแต่ช้าลง" }
      ]
    },
    {
      title: "2. การเข้าใจคำถาม",
      desc: "มีผลทันที ไม่ต้องสร้างดัชนีใหม่",
      items: [
        { key: "QUERY_NORMALIZE", type: "bool", label: "ทำความสะอาดคำถาม", hint: "ให้อยู่รูปเดียวกับตอนทำดัชนี" },
        { key: "QUERY_SYNONYM_EXPANSION", type: "bool", label: "ขยายคำพ้อง", hint: "เชื่อมคำไทยกับศัพท์อังกฤษ" },
        { key: "QUERY_MULTI", type: "bool", label: "Multi-Query", hint: "แตกคำถามเป็นหลายมุมมอง" }
      ]
    },
    {
      title: "3. การค้นหาและจัดอันดับ",
      desc: "ปรับแล้วลองถามใหม่เพื่อดูผลต่าง",
      items: [
        { key: "RETRIEVAL_MODE", type: "select", label: "วิธีค้นหา", opts: ["hybrid", "bm25", "dense"], hint: "hybrid คือรวมสองวิธีด้วย RRF" },
        { key: "TOP_K_FIRST", type: "num", label: "ผลจากชั้นแรก", hint: "จำนวนผู้สมัครก่อน rerank" },
        { key: "RRF_K", type: "num", label: "ค่า k ของ RRF", hint: "ยิ่งสูงยิ่งเกลี่ยน้ำหนักอันดับ" },
        { key: "USE_RERANK", type: "bool", label: "เปิด Re-ranking", hint: "จัดอันดับใหม่ด้วยสัญญาณละเอียด" },
        { key: "RERANK_TITLE_BOOST", type: "num", label: "โบนัสตรงคำถามหลัก", hint: "0 ถึง 1", step: 0.01 },
        { key: "RERANK_TAG_BOOST", type: "num", label: "โบนัสตรง tags", hint: "0 ถึง 1", step: 0.01 },
        { key: "USE_METADATA_FILTER", type: "bool", label: "เปิดตัวกรอง Metadata", hint: "กรองตามระดับและหมวด" }
      ]
    },
    {
      title: "4. การสร้างคำตอบและความปลอดภัย",
      desc: "กลุ่มนี้คือด่านป้องกัน Hallucination",
      items: [
        { key: "TOP_K_CONTEXT", type: "num", label: "จำนวนเอกสารที่ใช้ตอบ", hint: "ส่งเข้าขั้นตอนเรียบเรียง" },
        { key: "GROUNDING_THRESHOLD", type: "num", label: "เกณฑ์หลักฐานขั้นต่ำ", hint: "ต่ำกว่านี้ระบบจะปฏิเสธ", step: 0.01 },
        { key: "REQUIRE_CITATION", type: "bool", label: "บังคับแนบแหล่งอ้างอิง", hint: "ให้ตรวจสอบย้อนกลับได้" },
        { key: "SAFETY_GUARD", type: "bool", label: "เปิด Safety Guard", hint: "บล็อกคำขอคำแนะนำลงทุน" },
        { key: "FRESHNESS_WARNING", type: "bool", label: "เตือนข้อมูลล้าสมัย", hint: "ตรวจจากเดือนที่ทบทวน" },
        { key: "FRESHNESS_MONTHS", type: "num", label: "อายุข้อมูลที่ยอมรับ", hint: "หน่วยเป็นเดือน" }
      ]
    },
    {
      title: "5. เชื่อมต่อ LLM จริง (ทางเลือก)",
      desc: "ปิดไว้เป็นค่าเริ่มต้น ระบบทำงานได้ครบโดยไม่ต้องใช้ API Key — คีย์เก็บใน localStorage ของเครื่องคุณเท่านั้น",
      items: [
        { key: "USE_LLM", type: "bool", label: "ใช้ LLM เรียบเรียงคำตอบ", hint: "ยังยึดบริบทจากฐานความรู้เดิม" },
        { key: "LLM_PROVIDER", type: "select", label: "ผู้ให้บริการ", opts: ["gemini", "openai"], hint: "" },
        { key: "LLM_MODEL", type: "text", label: "ชื่อโมเดล", hint: "เช่น gemini-2.0-flash" },
        { key: "LLM_API_KEY", type: "text", label: "API Key", hint: "ไม่ถูกส่งไปที่อื่นนอกจากผู้ให้บริการที่เลือก" }
      ]
    }
  ];

  function renderSettings() {
    var host = $("settingsHost");
    var html = "";

    for (var g = 0; g < SETTING_GROUPS.length; g++) {
      var grp = SETTING_GROUPS[g];
      html += '<div class="set-group"><h3>' + esc(grp.title) + '</h3>' +
              '<div class="gdesc">' + esc(grp.desc) + '</div>';
      for (var i = 0; i < grp.items.length; i++) {
        var it = grp.items[i];
        var val = window.RAG_CONFIG[it.key];
        html += '<div class="set-row"><label>' + esc(it.label) +
                (it.hint ? '<span class="hint">' + esc(it.hint) + '</span>' : '') + '</label>';

        if (it.type === "bool") {
          html += '<div class="switch"><input type="checkbox" data-key="' + it.key + '"' +
                  (val ? " checked" : "") + '><span class="slider"></span></div>';
        } else if (it.type === "num") {
          html += '<input type="number" data-key="' + it.key + '" value="' + val +
                  '" step="' + (it.step || 1) + '">';
        } else if (it.type === "select") {
          html += '<select data-key="' + it.key + '">';
          for (var o = 0; o < it.opts.length; o++) {
            html += '<option' + (val === it.opts[o] ? " selected" : "") + '>' + esc(it.opts[o]) + '</option>';
          }
          html += '</select>';
        } else {
          html += '<input type="text" data-key="' + it.key + '" value="' + esc(val) + '">';
        }
        html += '</div>';
      }
      html += '</div>';
    }
    host.innerHTML = html;

    var inputs = host.querySelectorAll("[data-key]");
    for (var k = 0; k < inputs.length; k++) {
      inputs[k].addEventListener("change", function () {
        var key = this.getAttribute("data-key");
        var v;
        if (this.type === "checkbox") v = this.checked;
        else if (this.type === "number") v = parseFloat(this.value);
        else v = this.value;
        window.RAG_CONFIG[key] = v;
        saveConfig();
        syncFilterUI();
        $("settingsStatus").textContent = "บันทึก " + key + " = " + v + " แล้ว";
      });
    }

    $("resetCfgBtn").onclick = function () {
      for (var key in window.RAG_CONFIG_DEFAULT) {
        if (Object.prototype.hasOwnProperty.call(window.RAG_CONFIG_DEFAULT, key)) {
          window.RAG_CONFIG[key] = window.RAG_CONFIG_DEFAULT[key];
        }
      }
      saveConfig();
      renderSettings();
      syncFilterUI();
      rebuild();
      $("settingsStatus").textContent = "คืนค่าเริ่มต้นและสร้างดัชนีใหม่แล้ว";
    };
    $("rebuildBtn").onclick = function () {
      rebuild();
      $("settingsStatus").textContent = "สร้างดัชนีใหม่เรียบร้อย";
    };

    syncFilterUI();
  }

  function rebuild() {
    showStats(window.RagPipeline.buildIndex());
  }

  /* แสดงสถิติที่แถบบนแบบนับไต่ขึ้น
   * ใช้ที่เดียวทั้งตอนเปิดเว็บและตอนสร้างดัชนีใหม่
   * ทำให้เห็นชัดว่าการเปลี่ยนค่าคอนฟิกส่งผลต่อจำนวน chunk และคลังคำจริง */
  function showStats(b) {
    countUp($("statDocs"), b.docs, fmtInt, 700);
    countUp($("statChunks"), b.chunkStats.count, fmtInt, 850);
    countUp($("statVocab"), b.indexStats.vocabulary, fmtInt, 1000);
    countUp($("statTime"), b.timing.total, fmtFixed(1, " ms"), 700);
  }

  function syncFilterUI() {
    $("filterLevel").value = window.RAG_CONFIG.FILTER_LEVEL;
    $("filterMode").value = window.RAG_CONFIG.RETRIEVAL_MODE;
    var sel = $("filterCategory");
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].text === window.RAG_CONFIG.FILTER_CATEGORY) { sel.selectedIndex = i; break; }
    }
    updateFilterNote();
  }

  /* =========================================================
   *  บันทึกค่าลง localStorage
   * ========================================================= */
  function saveConfig() {
    try {
      localStorage.setItem("traderag_config", JSON.stringify(window.RAG_CONFIG));
    } catch (e) { /* โหมดส่วนตัวหรือปิดการเก็บข้อมูล — ข้ามไป */ }
  }

  function loadSavedConfig() {
    try {
      var raw = localStorage.getItem("traderag_config");
      if (!raw) return;
      var saved = JSON.parse(raw);
      for (var k in saved) {
        if (Object.prototype.hasOwnProperty.call(window.RAG_CONFIG, k)) {
          window.RAG_CONFIG[k] = saved[k];
        }
      }
    } catch (e) { /* ข้อมูลเสียหาย — ใช้ค่าเริ่มต้น */ }
  }

  /* ---------- เริ่มทำงาน ---------- */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
