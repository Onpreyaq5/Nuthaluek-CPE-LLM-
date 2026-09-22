"use client";

import { useMemo, useState } from "react";
import { Check, ChevronDown, Search, Users } from "lucide-react";
import {
  CATEGORY_LABEL,
  DAY_SHORT,
  categoryStyle,
  hhmm,
  type Course,
} from "../lib/types";

function whenText(meetings: Course["sections"][number]["meetings"]): string {
  return meetings
    .map((m) => `${DAY_SHORT[m.day]} ${hhmm(m.start_min)}-${hhmm(m.end_min)}`)
    .join(" · ");
}

/** รายการวิชา + เลือกหมู่เรียน — กดที่หมู่เพื่อเพิ่ม/เอาออกจากแผน */
export function CoursePicker({
  courses,
  selectedIds,
  onToggle,
  clashingIds = new Set<string>(),
}: {
  courses: Course[];
  selectedIds: string[];
  onToggle: (sectionId: string) => void;
  clashingIds?: Set<string>;
}) {
  const [query, setQuery] = useState("");
  const [year, setYear] = useState<string>("");
  const [openCode, setOpenCode] = useState<string | null>(null);
  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return courses.filter((c) => {
      if (year && String(c.suggested_year ?? "") !== year) return false;
      if (!q) return true;
      return (
        c.course_code.toLowerCase().includes(q) ||
        c.course_name.toLowerCase().includes(q)
      );
    });
  }, [courses, query, year]);

  const years = useMemo(
    () => Array.from(new Set(courses.map((c) => c.suggested_year).filter(Boolean))).sort() as number[],
    [courses],
  );

  return (
    <div className="flex h-full flex-col">
      {/* ตัวกรอง */}
      <div className="space-y-2 border-b border-slate-200 p-3">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <input
            className="input pl-9"
            placeholder="ค้นรหัสวิชา หรือชื่อวิชา"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="ค้นหารายวิชา"
          />
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setYear("")}
            className={`chip ${year === "" ? "border-brand-300 bg-brand-50 text-brand-700" : "border-slate-200 bg-white text-slate-600"}`}
          >
            ทุกชั้นปี
          </button>
          {years.map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => setYear(String(y))}
              className={`chip ${year === String(y) ? "border-brand-300 bg-brand-50 text-brand-700" : "border-slate-200 bg-white text-slate-600"}`}
            >
              ปี {y}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500">พบ {filtered.length} วิชา · กดที่หมู่เรียนเพื่อเพิ่มลงตาราง</p>
      </div>

      {/* รายการ */}
      <ul className="flex-1 divide-y divide-slate-100 overflow-y-auto">
        {filtered.map((c) => {
          const style = categoryStyle(c.category);
          const chosen = c.sections.filter((s) => selected.has(s.id));
          const open = openCode === c.course_code || chosen.length > 0;

          return (
            <li key={c.course_code}>
              <button
                type="button"
                onClick={() => setOpenCode(open && chosen.length === 0 ? null : c.course_code)}
                className="flex w-full items-start gap-2 px-3 py-2.5 text-left hover:bg-slate-50"
                aria-expanded={open}
              >
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${style.dot}`} aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5">
                    <span className="font-mono text-xs text-slate-500">{c.course_code}</span>
                    <span className="chip border-slate-200 bg-slate-50 text-[10px] text-slate-600">
                      {c.credits} นก.
                    </span>
                    {chosen.length > 0 && (
                      <span className="chip border-emerald-200 bg-emerald-50 text-[10px] text-emerald-700">
                        <Check className="h-3 w-3" aria-hidden /> เลือกแล้ว
                      </span>
                    )}
                  </span>
                  <span className="mt-0.5 block truncate text-sm font-medium text-slate-800">
                    {c.course_name}
                  </span>
                  <span className="mt-0.5 block text-[11px] text-slate-400">
                    {CATEGORY_LABEL[c.category] ?? c.category}
                    {c.prerequisites.length > 0 && ` · ต้องผ่าน ${c.prerequisites.join(", ")} ก่อน`}
                  </span>
                </span>
                <ChevronDown
                  className={`mt-1 h-4 w-4 shrink-0 text-slate-400 transition ${open ? "rotate-180" : ""}`}
                  aria-hidden
                />
              </button>

              {open && (
                <ul className="space-y-1 bg-slate-50/60 px-3 pb-2.5">
                  {c.sections.map((s) => {
                    const isSelected = selected.has(s.id);
                    const full = s.seat_left !== null && s.seat_left <= 0;
                    const clash = clashingIds.has(s.id);
                    return (
                      <li key={s.id}>
                        <button
                          type="button"
                          onClick={() => onToggle(s.id)}
                          className={[
                            "flex w-full items-center gap-2 rounded-lg border px-2.5 py-2 text-left text-xs transition",
                            isSelected
                              ? clash
                                ? "border-rose-300 bg-rose-50"
                                : "border-emerald-300 bg-emerald-50"
                              : full
                                ? "border-slate-200 bg-white opacity-60"
                                : "border-slate-200 bg-white hover:border-brand-300 hover:bg-brand-50",
                          ].join(" ")}
                        >
                          <span className="w-10 shrink-0 font-semibold text-slate-700">ม.{s.section}</span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-slate-700">{whenText(s.meetings)}</span>
                            <span className="block truncate text-[11px] text-slate-400">
                              {s.teachers[0] ?? "—"}
                            </span>
                          </span>
                          <span
                            className={[
                              "flex shrink-0 items-center gap-1 tabular-nums",
                              full ? "text-rose-600" : s.seat_left !== null && s.seat_left <= 5 ? "text-amber-600" : "text-slate-500",
                            ].join(" ")}
                          >
                            <Users className="h-3 w-3" aria-hidden />
                            {full ? "เต็ม" : `${s.seat_left} ที่`}
                          </span>
                          {isSelected && (
                            <Check
                              className={`h-4 w-4 shrink-0 ${clash ? "text-rose-600" : "text-emerald-600"}`}
                              aria-hidden
                            />
                          )}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
        {filtered.length === 0 && (
          <li className="px-3 py-8 text-center text-sm text-slate-500">
            ไม่พบรายวิชาที่ตรงกับคำค้น
          </li>
        )}
      </ul>
    </div>
  );
}
