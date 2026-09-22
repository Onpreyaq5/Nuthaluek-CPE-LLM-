"use client";

import {
  AlertTriangle,
  ArrowRightLeft,
  CheckCircle2,
  Clock,
  Coins,
  CopyX,
  FileWarning,
  Lock,
  Users,
  XCircle,
} from "lucide-react";
import type { Issue, PlanSummary } from "../lib/types";

/** ไอคอนและชื่อไทยของแต่ละรหัสปัญหา ตรงกับ C1-C6 / W1-W5 ของโมดูล 06 */
const ISSUE_META: Record<string, { label: string; Icon: typeof Clock; hint: string }> = {
  C1: { label: "เวลาเรียนชนกัน", Icon: Clock, hint: "เปลี่ยนหมู่เรียนของวิชาใดวิชาหนึ่ง" },
  C2: { label: "เวลาสอบชนกัน", Icon: FileWarning, hint: "เปลี่ยนหมู่เรียน หรือแจ้งฝ่ายวิชาการล่วงหน้า 1 สัปดาห์" },
  C3: { label: "ยังไม่ผ่านวิชาบังคับก่อน", Icon: Lock, hint: "ต้องสอบผ่านวิชาบังคับก่อนให้เรียบร้อยก่อน" },
  C4: { label: "หน่วยกิตไม่อยู่ในเกณฑ์", Icon: Coins, hint: "ปรับให้อยู่ระหว่าง 9–21 หน่วยกิต" },
  C5: { label: "ลงวิชาซ้ำ", Icon: CopyX, hint: "เอาวิชาที่ซ้ำออก เหลือไว้หมู่เดียว" },
  C6: { label: "ที่นั่งเต็ม", Icon: Users, hint: "เลือกหมู่อื่น หรือยื่นคำร้องขอเพิ่มที่นั่ง" },
  // W1 วัดจากคาบแรกถึงคาบสุดท้ายของวัน ไม่ใช่เวลาเรียนติดกันจริง
  // ถ้าเขียนว่า "เรียนติดกันยาว" แล้วแนะให้หาเวลาพักกลางวัน จะขัดกับตารางที่พักกลางวันอยู่แล้ว
  W1: { label: "อยู่มหาวิทยาลัยทั้งวัน", Icon: Clock, hint: "ถ้าไม่ไหว ลองสลับหมู่ให้เลิกเร็วขึ้น" },
  W2: { label: "มีช่องว่างนาน", Icon: Clock, hint: "เลือกหมู่ที่คาบอยู่ติดกันมากขึ้น" },
  W3: { label: "มีคาบเรียนเช้า", Icon: Clock, hint: "เลือกหมู่ที่ไม่มีคาบก่อน 09:00" },
  W4: { label: "ย้ายอาคารกระชั้น", Icon: ArrowRightLeft, hint: "เผื่อเวลาเดินทางระหว่างอาคาร" },
  W5: { label: "มามหาวิทยาลัยหลายวัน", Icon: Clock, hint: "รวมวิชาให้อยู่ในวันน้อยลง" },
};

function IssueRow({
  issue,
  onApply,
}: {
  issue: Issue;
  onApply?: (from: string, to: string) => void;
}) {
  const meta = ISSUE_META[issue.code] ?? {
    label: issue.message_key || issue.code,
    Icon: AlertTriangle,
    hint: "",
  };
  const error = issue.severity === "ERROR";
  const { Icon } = meta;

  return (
    <li
      className={[
        "rounded-lg border p-3",
        error ? "border-rose-200 bg-rose-50" : "border-amber-200 bg-amber-50",
      ].join(" ")}
    >
      <div className="flex items-start gap-2.5">
        <Icon
          className={["mt-0.5 h-4 w-4 shrink-0", error ? "text-rose-600" : "text-amber-600"].join(" ")}
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <p className={["text-sm font-semibold", error ? "text-rose-900" : "text-amber-900"].join(" ")}>
            {meta.label}
            <span className="ml-1.5 font-mono text-[10px] font-normal opacity-60">{issue.code}</span>
          </p>
          <p className="mt-0.5 break-words text-sm text-slate-700">{issue.message_th}</p>
          {meta.hint && <p className="mt-1 text-xs text-slate-500">แนะนำ: {meta.hint}</p>}

          {issue.suggestions?.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {issue.suggestions.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => s.from && onApply?.(s.from, s.to)}
                  disabled={!onApply || !s.from}
                  className="chip border-brand-300 bg-white text-brand-700 hover:bg-brand-50 disabled:opacity-60"
                >
                  <ArrowRightLeft className="h-3 w-3" aria-hidden />
                  เปลี่ยนเป็น {s.to}
                  {s.when && <span className="font-normal opacity-70">· {s.when}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </li>
  );
}

export function IssuePanel({
  conflicts,
  warnings,
  summary,
  onApplySuggestion,
}: {
  conflicts: Issue[];
  warnings: Issue[];
  summary?: PlanSummary;
  onApplySuggestion?: (from: string, to: string) => void;
}) {
  const errors = conflicts.filter((c) => c.severity === "ERROR");
  const soft = [...conflicts.filter((c) => c.severity !== "ERROR"), ...warnings];
  const clean = errors.length === 0;

  return (
    <div className="space-y-3">
      {/* สรุปหัวเรื่อง — บอกผลทันทีว่าลงได้หรือไม่ */}
      <div
        className={[
          "flex items-start gap-3 rounded-lg border p-3",
          clean ? "border-emerald-200 bg-emerald-50" : "border-rose-200 bg-rose-50",
        ].join(" ")}
      >
        {clean ? (
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" aria-hidden />
        ) : (
          <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" aria-hidden />
        )}
        <div className="min-w-0">
          <p className={["font-semibold", clean ? "text-emerald-900" : "text-rose-900"].join(" ")}>
            {clean ? "แผนนี้ลงทะเบียนได้" : `ลงทะเบียนไม่ได้ — ติดปัญหา ${errors.length} เรื่อง`}
          </p>
          {summary && (
            <p className="mt-0.5 text-sm text-slate-600">
              {summary.total_courses} วิชา · {summary.total_credits} หน่วยกิต
              {summary.credit_status === "ok" && (
                <span className="text-emerald-700"> (อยู่ในเกณฑ์ {summary.min_credits}–{summary.max_credits})</span>
              )}
              {summary.credit_status === "under" && (
                <span className="text-rose-700"> (ยังไม่ถึงขั้นต่ำ {summary.min_credits})</span>
              )}
              {summary.credit_status === "over" && (
                <span className="text-rose-700"> (เกินเพดาน {summary.max_credits})</span>
              )}
              {summary.free_days.length > 0 && (
                <span className="text-slate-500"> · ว่าง {summary.free_days.join(" ")}</span>
              )}
            </p>
          )}
          {clean && soft.length === 0 && (
            <p className="mt-0.5 text-sm text-emerald-700">
              ไม่มีเวลาเรียนหรือเวลาสอบทับกัน และผ่านเงื่อนไขวิชาบังคับก่อนครบ
            </p>
          )}
        </div>
      </div>

      {errors.length > 0 && (
        <section>
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-rose-700">
            ต้องแก้ก่อนถึงจะลงได้
          </h3>
          <ul className="space-y-2">
            {errors.map((c, i) => (
              <IssueRow key={`${c.code}-${i}`} issue={c} onApply={onApplySuggestion} />
            ))}
          </ul>
        </section>
      )}

      {soft.length > 0 && (
        <section>
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-amber-700">
            ข้อควรระวัง (ลงได้ แต่ควรรู้ไว้)
          </h3>
          <ul className="space-y-2">
            {soft.map((c, i) => (
              <IssueRow key={`${c.code}-w${i}`} issue={c} onApply={onApplySuggestion} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
