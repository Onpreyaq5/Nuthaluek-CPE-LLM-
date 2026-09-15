/* =============================================================
 *  mindmap.js — สร้าง Mind Map เป็น SVG จากโครงสร้างข้อมูลต้นไม้
 *  ใช้อัลกอริทึมจัดวางแบบ Horizontal Tree
 *   - โหนดใบกินพื้นที่แนวตั้งตามจำนวนบรรทัดของข้อความ
 *   - โหนดพ่อวางไว้กึ่งกลางระหว่างลูกคนแรกกับลูกคนสุดท้าย
 * ============================================================= */

window.RagMindmap = (function () {

  var COLORS = ["#d5ff3f", "#b8c3d1", "#e2c47e", "#c5b8dc", "#e59a9a", "#a9c9b2"];

  /* ---------- ข้อมูลแผนที่ ---------- */
  var MAPS = {

    system: {
      title: "โครงสร้างระบบ TradeRAG",
      legend: "ระบบแบ่งเป็น 5 ส่วนหลัก ไล่จากข้อมูลดิบไปจนถึงหน้าจอที่ผู้ใช้เห็น",
      root: {
        label: "ระบบ TradeRAG",
        children: [
          {
            label: "1. ฐานความรู้", children: [
              { label: "ความรู้เบื้องต้น", children: [
                { label: "พื้นฐานการเทรด" }, { label: "การบริหารความเสี่ยง" },
                { label: "จิตวิทยาการเทรด" }, { label: "เทคนิคเบื้องต้น" },
                { label: "ปัจจัยพื้นฐาน" }, { label: "กฎหมายและความปลอดภัย" }
              ]},
              { label: "ความรู้เทคนิคขั้นสูง", children: [
                { label: "อินดิเคเตอร์" }, { label: "รูปแบบราคา" },
                { label: "Smart Money / Wyckoff" }, { label: "กลยุทธ์และระบบเทรด" }
              ]},
              { label: "Metadata ต่อเอกสาร", children: [
                { label: "รหัส หมวด ระดับความยาก" },
                { label: "tags และคำถามสำรอง" },
                { label: "เดือนที่ทบทวนล่าสุด" }
              ]}
            ]
          },
          {
            label: "2. ขั้นตอนการทำงาน", children: [
              { label: "ทำความสะอาด + ตัดข้อมูลซ้ำ" },
              { label: "ตัด Chunk 420 / overlap 80" },
              { label: "สร้างดัชนี TF-IDF + BM25" },
              { label: "แปลงคำถาม + ขยายคำพ้อง" },
              { label: "ค้นแบบ Hybrid + RRF" },
              { label: "จัดอันดับใหม่ (Rerank)" },
              { label: "ตรวจ Guardrail" },
              { label: "เรียบเรียง + แนบอ้างอิง" }
            ]
          },
          {
            label: "3. การควบคุมคุณภาพ", children: [
              { label: "เกณฑ์หลักฐานขั้นต่ำ" },
              { label: "บังคับแนบแหล่งอ้างอิง" },
              { label: "วัดค่า Faithfulness" },
              { label: "เตือนข้อมูลล้าสมัย" },
              { label: "Safety Guard" }
            ]
          },
          {
            label: "4. การประเมินผล", children: [
              { label: "Golden Set จากคำถามสำรอง" },
              { label: "Hit@k / MRR / nDCG" },
              { label: "Ablation Study 5 ชุดค่า" },
              { label: "ทดสอบผลของขนาด Chunk" }
            ]
          },
          {
            label: "5. ส่วนติดต่อผู้ใช้", children: [
              { label: "ถาม-ตอบ พร้อมแหล่งอ้างอิง" },
              { label: "ตรวจสอบ Pipeline ทีละขั้น" },
              { label: "Problem Lab 10 ข้อ" },
              { label: "หน้าประเมินผล" },
              { label: "หน้าตั้งค่า RAG" }
            ]
          }
        ]
      }
    },

    trading: {
      title: "แผนที่ความรู้การเทรดในฐานข้อมูล",
      legend: "แบ่งเป็น 2 ชั้น คือความรู้เบื้องต้นที่ต้องรู้ก่อนลงสนาม และความรู้เทคนิคขั้นสูงสำหรับผู้ที่ผ่านพื้นฐานแล้ว",
      root: {
        label: "ความรู้การเทรด",
        children: [
          {
            label: "ความรู้เบื้องต้น", children: [
              { label: "พื้นฐานตลาด", children: [
                { label: "ประเภทสินทรัพย์ที่เทรดได้" },
                { label: "คำสั่งซื้อขาย 5 แบบ" },
                { label: "ต้นทุน: spread ค่าธรรมเนียม slippage" },
                { label: "Leverage และ Margin" },
                { label: "Long / Short และ Timeframe" },
                { label: "สภาพคล่องของตลาด" }
              ]},
              { label: "การบริหารความเสี่ยง", children: [
                { label: "กฎเสี่ยง 1-2% ต่อไม้" },
                { label: "คำนวณขนาดสถานะ" },
                { label: "การวางจุดตัดขาดทุน" },
                { label: "อัตราส่วน R:R และ Expectancy" },
                { label: "Drawdown และการฟื้นตัว" },
                { label: "Kelly และ Correlation" }
              ]},
              { label: "จิตวิทยาการเทรด", children: [
                { label: "FOMO และการไล่ราคา" },
                { label: "Revenge Trading" },
                { label: "อคติทางความคิด 5 แบบ" },
                { label: "แผนการเทรดและบันทึก" }
              ]},
              { label: "เทคนิคเบื้องต้น", children: [
                { label: "แนวรับ แนวต้าน" },
                { label: "แนวโน้มและโครงสร้างราคา" },
                { label: "การอ่านแท่งเทียน" },
                { label: "ปริมาณซื้อขายและ Breakout" },
                { label: "วิเคราะห์หลายกรอบเวลา" }
              ]},
              { label: "ปัจจัยพื้นฐาน", children: [
                { label: "งบการเงินและอัตราส่วน" },
                { label: "ข่าวเศรษฐกิจ FOMC CPI NFP" }
              ]},
              { label: "กฎหมายและความปลอดภัย", children: [
                { label: "สังเกตการหลอกลวงลงทุน" },
                { label: "ภาษีและความปลอดภัยบัญชี" }
              ]}
            ]
          },
          {
            label: "ความรู้เทคนิคขั้นสูง", children: [
              { label: "อินดิเคเตอร์", children: [
                { label: "MA / EMA และ Golden Cross" },
                { label: "RSI และการอ่านที่ถูกวิธี" },
                { label: "MACD และ Histogram" },
                { label: "Bollinger Bands และ Squeeze" },
                { label: "ATR ใช้ตั้งจุดตัดขาดทุน" },
                { label: "ADX กรองสภาพตลาด" },
                { label: "Ichimoku ทั้ง 5 เส้น" },
                { label: "Stochastic และ Divergence" },
                { label: "VWAP และ Anchored VWAP" }
              ]},
              { label: "รูปแบบราคา", children: [
                { label: "Head and Shoulders" },
                { label: "Double Top / Double Bottom" },
                { label: "สามเหลี่ยม ธง และลิ่ม" },
                { label: "แท่งเทียนกลับตัว" }
              ]},
              { label: "Smart Money Concept", children: [
                { label: "Market Structure BOS / CHoCH" },
                { label: "Order Block และ Liquidity" },
                { label: "Fair Value Gap" },
                { label: "Wyckoff และ Spring" },
                { label: "Volume Profile และ POC" },
                { label: "Supply / Demand Zone" }
              ]},
              { label: "เครื่องมือคำนวณเป้าหมาย", children: [
                { label: "Fibonacci Retracement" },
                { label: "Elliott Wave และกฎ 3 ข้อ" }
              ]},
              { label: "กลยุทธ์และระบบเทรด", children: [
                { label: "สไตล์การเทรด 4 แบบ" },
                { label: "Backtesting และ Overfitting" },
                { label: "ตามแนวโน้ม vs กลับค่าเฉลี่ย" },
                { label: "Algorithmic Trading" },
                { label: "กลยุทธ์การออกจากออเดอร์" },
                { label: "ความต่างของตลาดคริปโท" }
              ]}
            ]
          }
        ]
      }
    },

    problem: {
      title: "แผนที่ปัญหาและการแก้ไข 10 ข้อ",
      legend: "จัดกลุ่มตามชั้นที่เกิดปัญหา แต่ละใบคือวิธีแก้ที่ทำไว้จริงใน Source Code",
      root: {
        label: "ปัญหาของ RAG System",
        children: [
          {
            label: "ชั้นเตรียมข้อมูล", children: [
              { label: "01 ข้อมูลซ้ำและไม่สะอาด", children: [
                { label: "แก้: normalize + fingerprint dedupe" }
              ]},
              { label: "02 ขนาด Chunk ไม่เหมาะสม", children: [
                { label: "แก้: ตัดตามโครงสร้าง + overlap 80" }
              ]}
            ]
          },
          {
            label: "ชั้นค้นหา", children: [
              { label: "03 คำไทย-อังกฤษไม่ตรงกัน", children: [
                { label: "แก้: n-gram + พจนานุกรมคำพ้อง" }
              ]},
              { label: "04 คำถามสั้นหรือกำกวม", children: [
                { label: "แก้: Multi-Query หลายมุมมอง" }
              ]},
              { label: "05 ใช้วิธีค้นเดียวแล้วแพ้", children: [
                { label: "แก้: Hybrid BM25 + Vector + RRF" }
              ]},
              { label: "06 เอกสารที่ถูกอันดับต่ำ", children: [
                { label: "แก้: Re-ranking ด้วยสัญญาณละเอียด" }
              ]},
              { label: "07 ตัวกรอง Metadata ผิด", children: [
                { label: "แก้: แสดงจำนวนที่ถูกกรองออก" }
              ]}
            ]
          },
          {
            label: "ชั้นสร้างคำตอบ", children: [
              { label: "08 Hallucination", children: [
                { label: "แก้: เกณฑ์หลักฐาน + บังคับอ้างอิง" }
              ]},
              { label: "10 คำแนะนำลงทุนและข้อมูลเก่า", children: [
                { label: "แก้: Safety Guard + เตือนความสด" }
              ]}
            ]
          },
          {
            label: "ชั้นวัดผล", children: [
              { label: "09 ไม่มีตัวเลขยืนยัน", children: [
                { label: "แก้: Golden Set + Ablation Study" }
              ]}
            ]
          }
        ]
      }
    }
  };

  /* ---------- ตัวช่วย ---------- */
  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  /* ตัดข้อความเป็นหลายบรรทัดตามความกว้างกล่อง */
  function wrap(text, maxChars) {
    if (text.length <= maxChars) return [text];
    var words = text.split(" ");
    var lines = [], cur = "";
    for (var i = 0; i < words.length; i++) {
      var test = cur ? cur + " " + words[i] : words[i];
      if (test.length > maxChars && cur) { lines.push(cur); cur = words[i]; }
      else cur = test;
    }
    if (cur) lines.push(cur);

    // ถ้ายังมีบรรทัดที่ยาวเกิน (ภาษาไทยไม่มีช่องว่าง) ให้หั่นตรง ๆ
    var out = [];
    for (var j = 0; j < lines.length; j++) {
      var L = lines[j];
      while (L.length > maxChars) { out.push(L.slice(0, maxChars)); L = L.slice(maxChars); }
      if (L) out.push(L);
    }
    return out.slice(0, 3);
  }

  /* ---------- จัดวางตำแหน่ง ---------- */
  var GEO = [
    { x: 16,  w: 186, chars: 20, size: 13.5 },   // depth 0
    { x: 232, w: 208, chars: 24, size: 12.5 },   // depth 1
    { x: 470, w: 232, chars: 27, size: 12 },     // depth 2
    { x: 732, w: 292, chars: 34, size: 11.5 }    // depth 3
  ];

  function prepare(node, depth) {
    var g = GEO[Math.min(depth, GEO.length - 1)];
    node.depth = depth;
    node.lines = wrap(node.label, g.chars);
    node.h = node.lines.length * 16 + 14;
    if (node.children && node.children.length) {
      for (var i = 0; i < node.children.length; i++) prepare(node.children[i], depth + 1);
    }
  }

  function assignY(node, cursor) {
    if (!node.children || !node.children.length) {
      node.y = cursor.v + node.h / 2;
      cursor.v += node.h + 10;
      return;
    }
    var firstY, lastY;
    for (var i = 0; i < node.children.length; i++) {
      assignY(node.children[i], cursor);
      if (i === 0) firstY = node.children[i].y;
      lastY = node.children[i].y;
      // เว้นช่องระหว่างกลุ่มลูกของโหนดคนละพ่อ
      if (i < node.children.length - 1 && node.children[i].children) cursor.v += 8;
    }
    node.y = (firstY + lastY) / 2;
  }

  function collect(node, list) {
    list.push(node);
    if (node.children) for (var i = 0; i < node.children.length; i++) collect(node.children[i], list);
    return list;
  }

  /* ---------- วาด SVG ---------- */
  function build(mapKey) {
    var map = MAPS[mapKey] || MAPS.system;
    var root = JSON.parse(JSON.stringify(map.root));

    prepare(root, 0);
    var cursor = { v: 26 };
    assignY(root, cursor);
    var H = cursor.v + 26;
    var W = 1040;

    // กำหนดสีตามสาขาหลัก
    if (root.children) {
      for (var b = 0; b < root.children.length; b++) {
        var color = COLORS[b % COLORS.length];
        var branchNodes = collect(root.children[b], []);
        for (var n = 0; n < branchNodes.length; n++) branchNodes[n].color = color;
      }
    }
    root.color = "#f2f2ef";

    var edges = "", nodes = "";

    function draw(node) {
      var g = GEO[Math.min(node.depth, GEO.length - 1)];
      var x = g.x, w = g.w, h = node.h, y = node.y - h / 2;
      var color = node.color || "#d5ff3f";
      var isRoot = node.depth === 0;
      var isBranch = node.depth === 1;

      // เส้นเชื่อมไปลูก
      if (node.children) {
        for (var i = 0; i < node.children.length; i++) {
          var c = node.children[i];
          var cg = GEO[Math.min(c.depth, GEO.length - 1)];
          var x1 = x + w, y1 = node.y, x2 = cg.x, y2 = c.y;
          var mx = (x1 + x2) / 2;
          // class mm-edge ใช้สำหรับแอนิเมชันวาดเส้น (ดู style.css)
          // app.js จะวัดความยาวจริงของเส้นด้วย getTotalLength() แล้วส่งเข้ามาเป็นตัวแปร --len
          edges += '<path class="mm-edge" d="M' + x1 + ' ' + y1 + ' C' + mx + ' ' + y1 + ', ' + mx + ' ' + y2 +
                   ', ' + x2 + ' ' + y2 + '" fill="none" stroke="' + (c.color || color) +
                   '" stroke-width="' + (c.depth <= 2 ? 1.8 : 1.2) + '" opacity="' +
                   (c.depth <= 2 ? .65 : .4) + '"/>';
          draw(c);
        }
      }

      var fill = isRoot ? "#27292b" : (isBranch ? color + "26" : (node.depth === 2 ? color + "18" : "#1c1d1f"));
      var stroke = isRoot ? "#f2f2ef" : color;
      var sw = isRoot ? 2 : (isBranch ? 1.7 : 1.1);
      var op = node.depth >= 3 ? .55 : 1;

      nodes += '<g class="mm-node">';
      nodes += '<rect x="' + x + '" y="' + y + '" width="' + w + '" height="' + h +
               '" rx="9" fill="' + fill + '" stroke="' + stroke + '" stroke-width="' + sw +
               '" opacity="' + op + '"/>';
      for (var k = 0; k < node.lines.length; k++) {
        var ty = y + 15 + k * 16;
        nodes += '<text x="' + (x + 11) + '" y="' + ty + '" font-size="' + g.size +
                 '" fill="' + (isRoot || isBranch ? "#f2f2ef" : "#c8c9c4") +
                 '" font-weight="' + (isRoot || isBranch ? 600 : 400) + '">' +
                 esc(node.lines[k]) + '</text>';
      }
      nodes += '</g>';
    }

    draw(root);

    var svg = '<svg viewBox="0 0 ' + W + ' ' + H + '" xmlns="http://www.w3.org/2000/svg">' +
              '<rect width="' + W + '" height="' + H + '" fill="none"/>' +
              edges + nodes + '</svg>';

    return { svg: svg, title: map.title, legend: map.legend, branches: root.children || [] };
  }

  return { build: build, MAPS: MAPS, COLORS: COLORS };
})();
