"use client";

import { useEffect, useRef, useState } from "react";
import { BookMarked, Loader2, Send, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import type { ChatResult } from "../lib/types";

type Msg = { role: "user" | "bot"; text: string; data?: ChatResult };

const EXAMPLES = [
  "ลงทะเบียนได้กี่หน่วยกิตต่อเทอม",
  "ถอนรายวิชาได้ถึงเมื่อไหร่",
  "ปี 2 เทอม 1 ต้องเรียนวิชาอะไรบ้าง",
  "ได้ F ต้องทำยังไง",
  "เกรด B+ ได้กี่แต้ม",
  "วิชาชีพเลือกมีอะไรบ้าง",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ chunks: number; llm: string } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.chatStatus()
      .then((s) => setStatus({ chunks: s.knowledge.chunks, llm: s.llm }))
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setBusy(true);
    try {
      const r = await api.chat({ question: q });
      setMessages((m) => [...m, { role: "bot", text: r.answer, data: r }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: `เกิดข้อผิดพลาด: ${(e as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="card p-4">
        <h1 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
          <Sparkles className="h-5 w-5 text-brand-600" aria-hidden />
          ถามเรื่องระเบียบและหลักสูตร
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          ตอบจากข้อบังคับการศึกษา โครงสร้างหลักสูตร ปฏิทินการศึกษา และคำอธิบายรายวิชา
          <strong className="text-slate-800"> พร้อมบอกแหล่งอ้างอิงทุกครั้ง</strong>
        </p>
        {status && (
          <p className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <BookMarked className="h-3.5 w-3.5" aria-hidden /> เอกสาร {status.chunks} ส่วน
            </span>
            <span className="flex items-center gap-1">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
              โหมด {status.llm === "gemini" ? "Gemini" : "อ้างอิงเอกสารตรง (ไม่ใช้โมเดลภาษา)"}
            </span>
          </p>
        )}
      </div>

      {messages.length === 0 && (
        <div className="card p-4">
          <p className="text-sm font-medium text-slate-700">ลองถามคำถามเหล่านี้</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {EXAMPLES.map((q) => (
              <button key={q} type="button" onClick={() => ask(q)} className="chip border-slate-200 bg-white text-slate-700 hover:border-brand-300 hover:bg-brand-50">
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : ""}>
            {m.role === "user" ? (
              <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-sm text-white">
                {m.text}
              </p>
            ) : (
              <div className="card p-4">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{m.text}</p>

                {m.data && m.data.sources.length > 0 && (
                  <div className="mt-3 border-t border-slate-100 pt-3">
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                      แหล่งอ้างอิง
                    </p>
                    <ul className="mt-1.5 space-y-1">
                      {m.data.sources.map((s, j) => (
                        <li key={s.doc_id} className="flex gap-2 text-xs text-slate-600">
                          <span className="font-mono text-slate-400">[{j + 1}]</span>
                          <span className="min-w-0">
                            <span className="block truncate font-medium text-slate-700">{s.title}</span>
                            {s.section && <span className="block truncate text-slate-500">{s.section}</span>}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {m.data && !m.data.grounded && (
                  <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    ระบบไม่มีข้อมูลเรื่องนี้ จึงไม่ตอบเดา — เป็นพฤติกรรมที่ตั้งใจให้เป็น
                  </p>
                )}

                {m.data && (
                  <p className="mt-2 text-[11px] text-slate-400">{m.data.disclaimer}</p>
                )}
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="card flex items-center gap-2 p-4 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> กำลังค้นเอกสาร...
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); ask(input); }}
        className="sticky bottom-4 flex gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
      >
        <input
          className="input border-0 focus:ring-0"
          placeholder="พิมพ์คำถาม เช่น ถอนรายวิชาได้ถึงเมื่อไหร่"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          aria-label="คำถาม"
        />
        <button type="submit" className="btn-primary shrink-0" disabled={busy || !input.trim()}>
          <Send className="h-4 w-4" aria-hidden />
          <span className="hidden sm:inline">ถาม</span>
        </button>
      </form>
    </div>
  );
}
