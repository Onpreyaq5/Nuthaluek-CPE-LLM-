"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  Download,
  Loader2,
  RotateCcw,
  Settings2,
  Sparkles,
} from "lucide-react";
import { CoursePicker } from "../components/CoursePicker";
import { IssuePanel } from "../components/IssuePanel";
import { Timetable } from "../components/Timetable";
import { api } from "../lib/api";
import { DEFAULT_STATE, loadState, saveState, type SavedState } from "../lib/storage";
import {
  CATEGORY_LABEL,
  CATEGORY_STYLE,
  DAY_TH,
  hhmm,
  type Course,
  type PlannedSection,
  type ValidateResult,
} from "../lib/types";

/** รวมข้อมูลหมู่เรียนที่เลือกให้อยู่ในรูปที่ตารางใช้ได้ */
function toPlanned(courses: Course[], ids: string[]): PlannedSection[] {
  const out: PlannedSection[] = [];
  for (const c of courses) {
    for (const s of c.sections) {
      if (!ids.includes(s.id)) continue;
      out.push({
        ...s,
        course_code: c.course_code,
        course_name: c.course_name,
        credits: c.credits,
        category: c.category,
        suggested_year: c.suggested_year,
        prerequisites: c.prerequisites,
      });
    }
  }
  return out;
}

/** แปลงวันที่+นาที เป็นรูปแบบเวลาท้องถิ่นของ iCalendar (YYYYMMDDTHHMMSS) */
function icsStamp(date: Date, minutes: number): string {
  const d = new Date(date);
  d.setHours(Math.floor(minutes / 60), minutes % 60, 0, 0);
  const p = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}` +
    `T${p(d.getHours())}${p(d.getMinutes())}00`
  );
}

/** ข้อความในไฟล์ .ics ต้อง escape อักขระพิเศษ ไม่งั้นไฟล์เสีย */
function icsText(value: string): string {
  return value.replace(/\\/g, "\\\\").replace(/[;,]/g, (c) => `\\${c}`).replace(/\r?\n/g, "\\n");
}

function downloadIcs(sections: PlannedSection[], term: string, termStart: string, weeks: number) {
  // ต้องมี DTSTART/DTEND เสมอ — VEVENT ที่ไม่มีจะถูกปฏิทินปฏิเสธทั้งไฟล์
  // (เดิมใส่แค่ RRULE กับ X-TIME ทำให้ Google Calendar นำเข้าไม่ได้เลย)
  const start = new Date(`${termStart}T00:00:00`);
  if (Number.isNaN(start.getTime())) return;

  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//RMUTT Study Planner//TH",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${icsText(`ตารางเรียน ${term}`)}`,
    "X-WR-TIMEZONE:Asia/Bangkok",
  ];
  const BYDAY = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"];

  for (const s of sections) {
    for (const [i, m] of s.meetings.entries()) {
      // วันแรกของคาบนี้ = วันเปิดเทอม (จันทร์) + จำนวนวันตาม day
      const first = new Date(start);
      first.setDate(first.getDate() + m.day);
      const kind = m.meeting_type === "lab" ? "ปฏิบัติ" : "บรรยาย";
      lines.push(
        "BEGIN:VEVENT",
        `UID:${s.id}-${i}@rmutt-planner`,
        `DTSTAMP:${icsStamp(new Date(), new Date().getHours() * 60 + new Date().getMinutes())}`,
        `DTSTART:${icsStamp(first, m.start_min)}`,
        `DTEND:${icsStamp(first, m.end_min)}`,
        `RRULE:FREQ=WEEKLY;BYDAY=${BYDAY[m.day]};COUNT=${weeks}`,
        `SUMMARY:${icsText(`${s.course_code} ${s.course_name}`)}`,
        `DESCRIPTION:${icsText(`หมู่ ${s.section} · ${kind} · ${s.credits} หน่วยกิต · ภาคการศึกษา ${term}`)}`,
        `LOCATION:${icsText(`${m.room} ${m.building}`)}`,
        "END:VEVENT",
      );
    }
  }
  lines.push("END:VCALENDAR");

  const blob = new Blob([lines.join("\r\n")], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ตารางเรียน-${term.replace("/", "-")}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function PlannerPage() {
  const [state, setState] = useState<SavedState>(DEFAULT_STATE);
  const [courses, setCourses] = useState<Course[]>([]);
  const [terms, setTerms] = useState<string[]>([]);
  const [result, setResult] = useState<ValidateResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [planning, setPlanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPrefs, setShowPrefs] = useState(false);
  const [skipped, setSkipped] = useState<{ course_code: string; reason: string }[]>([]);
  const [termInfo, setTermInfo] = useState({ termStart: "", weeks: 16 });
  // ต้องเป็น state ไม่ใช่ ref: ถ้าใช้ ref เอฟเฟกต์บันทึกจะเห็น hydrated=true
  // ตั้งแต่รอบ mount แรก แล้วบันทึกค่าเริ่มต้นทับแผนที่ผู้ใช้เคยเก็บไว้
  // (เคยเป็นบั๊กจริง: เปิดหน้าใหม่ทีไรแผนหายทุกครั้ง)
  const [hydrated, setHydrated] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);   // เพิ่มค่าเพื่อสั่งโหลดรายวิชาใหม่

  // โหลดสถานะที่เคยบันทึกไว้ในเบราว์เซอร์
  useEffect(() => {
    setState(loadState());
    setHydrated(true);
  }, []);

  // โหลดรายวิชาตามเทอม
  useEffect(() => {
    if (!hydrated) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .courses({ term: state.term })
      .then((d) => {
        if (cancelled) return;
        setCourses(d.courses);
        setTerms(d.available_terms);
        setTermInfo({ termStart: d.term_start ?? "", weeks: d.weeks ?? 16 });
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setError(e.message);
        // ต้องล้างรายวิชาของเทอมก่อนหน้าทิ้ง ไม่งั้นหัวข้อขึ้นเทอมใหม่
        // แต่รายการวิชายังเป็นของเทอมเก่า ผู้ใช้จะเลือกผิดเทอมโดยไม่รู้ตัว
        setCourses([]);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [state.term, hydrated, reloadKey]);

  useEffect(() => {
    if (hydrated) saveState(state);
  }, [state, hydrated]);

  const planned = useMemo(() => toPlanned(courses, state.selectedIds), [courses, state.selectedIds]);

  // ตรวจตารางชนทุกครั้งที่แผนเปลี่ยน
  useEffect(() => {
    if (state.selectedIds.length === 0) {
      setResult(null);
      return;
    }
    let cancelled = false;
    setChecking(true);
    api
      .validate({
        term: state.term,
        section_ids: state.selectedIds,
        passed_courses: state.passedCourses,
      })
      .then((r) => {
        if (cancelled) return;
        setResult(r);
        setError(null);   // สำเร็จแล้วต้องเก็บกล่องแดงเดิมออก ไม่งั้นค้างจนกว่าจะเปลี่ยนเทอม
      })
      .catch((e: Error) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setChecking(false));
    return () => {
      cancelled = true;
    };
  }, [state.selectedIds, state.term, state.passedCourses]);

  const clashingIds = useMemo(() => {
    const ids = new Set<string>();
    for (const c of result?.conflicts ?? []) {
      if (c.severity === "ERROR") c.subjects.forEach((s) => ids.add(s));
    }
    return ids;
  }, [result]);

  const toggle = useCallback((sectionId: string) => {
    setSkipped([]);   // ผู้ใช้แก้แผนเองแล้ว รายการเดิมจากการจัดอัตโนมัติไม่ตรงอีกต่อไป
    setState((prev) => ({
      ...prev,
      selectedIds: prev.selectedIds.includes(sectionId)
        ? prev.selectedIds.filter((x) => x !== sectionId)
        : [...prev.selectedIds, sectionId],
    }));
  }, []);

  const applySuggestion = useCallback((from: string, to: string) => {
    setSkipped([]);
    setState((prev) => ({
      ...prev,
      selectedIds: prev.selectedIds.map((x) => (x === from ? to : x)),
    }));
  }, []);

  async function autoPlan() {
    setPlanning(true);
    setError(null);
    try {
      const r = await api.autoplan({
        term: state.term,
        student_year: state.studentYear ?? undefined,
        passed_courses: state.passedCourses,
        preferences: {
          avoid_morning: state.preferences.avoidMorning,
          free_days: state.preferences.freeDays,
          max_credits: state.preferences.maxCredits,
        },
      });
      setState((prev) => ({ ...prev, selectedIds: r.plan.map((s) => s.id) }));
      setSkipped(r.skipped);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPlanning(false);
    }
  }

  const credits = planned.reduce((sum, s) => sum + s.credits, 0);

  return (
    <div className="space-y-4">
      {/* แถบควบคุมด้านบน */}
      <div className="card p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label" htmlFor="term">ภาคการศึกษา</label>
            <select
              id="term"
              className="input mt-1 w-40"
              value={state.term}
              onChange={(e) => {
                setSkipped([]);
                setState((p) => ({ ...p, term: e.target.value, selectedIds: [] }));
              }}
            >
              {(terms.length ? terms : [state.term]).map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="label" htmlFor="year">ชั้นปีของคุณ</label>
            <select
              id="year"
              className="input mt-1 w-32"
              value={state.studentYear ?? ""}
              onChange={(e) =>
                setState((p) => ({ ...p, studentYear: e.target.value ? Number(e.target.value) : null }))
              }
            >
              <option value="">ไม่ระบุ</option>
              {[1, 2, 3, 4].map((y) => (
                <option key={y} value={y}>ปี {y}</option>
              ))}
            </select>
          </div>

          <button type="button" className="btn-ghost" onClick={() => setShowPrefs((v) => !v)}>
            <Settings2 className="h-4 w-4" aria-hidden />
            เงื่อนไขของฉัน
          </button>

          <button type="button" className="btn-primary" onClick={autoPlan} disabled={planning}>
            {planning ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Sparkles className="h-4 w-4" aria-hidden />}
            {planning ? "กำลังจัดให้..." : "ให้ระบบจัดตารางให้"}
          </button>

          <div className="ml-auto flex items-center gap-2">
            <button
              type="button"
              className="btn-ghost"
              onClick={() => downloadIcs(planned, state.term, termInfo.termStart, termInfo.weeks)}
              disabled={planned.length === 0 || !termInfo.termStart}
              title="บันทึกเป็นไฟล์ปฏิทิน เปิดใน Google Calendar ได้"
              aria-label="ส่งออกเป็นไฟล์ปฏิทิน"
            >
              <Download className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">ส่งออกปฏิทิน</span>
            </button>
            <button
              type="button"
              className="btn-danger"
              onClick={() => { setState((p) => ({ ...p, selectedIds: [] })); setSkipped([]); }}
              disabled={planned.length === 0}
              aria-label="ล้างแผนทั้งหมด"
            >
              <RotateCcw className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">ล้างแผน</span>
            </button>
          </div>
        </div>

        {showPrefs && (
          <div className="mt-4 grid gap-4 border-t border-slate-200 pt-4 sm:grid-cols-3">
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-brand-600"
                checked={state.preferences.avoidMorning}
                onChange={(e) =>
                  setState((p) => ({ ...p, preferences: { ...p.preferences, avoidMorning: e.target.checked } }))
                }
              />
              ไม่เอาคาบก่อน 09:00
            </label>

            <div>
              <span className="label">วันที่อยากว่าง</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {DAY_TH.map((d) => {
                  const on = state.preferences.freeDays.includes(d);
                  return (
                    <button
                      key={d}
                      type="button"
                      onClick={() =>
                        setState((p) => ({
                          ...p,
                          preferences: {
                            ...p.preferences,
                            freeDays: on
                              ? p.preferences.freeDays.filter((x) => x !== d)
                              : [...p.preferences.freeDays, d],
                          },
                        }))
                      }
                      className={`chip ${on ? "border-brand-300 bg-brand-50 text-brand-700" : "border-slate-200 bg-white text-slate-600"}`}
                    >
                      {d}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="label" htmlFor="maxcr">
                หน่วยกิตสูงสุด ({state.preferences.maxCredits})
              </label>
              <input
                id="maxcr"
                type="range"
                min={9}
                max={21}
                value={state.preferences.maxCredits}
                onChange={(e) =>
                  setState((p) => ({ ...p, preferences: { ...p.preferences, maxCredits: Number(e.target.value) } }))
                }
                className="mt-2 w-full accent-brand-600"
              />
              <p className="text-xs text-slate-500">ระเบียบกำหนด 9–21 หน่วยกิตต่อเทอมปกติ</p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="card flex flex-wrap items-center justify-between gap-3 border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          <span className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
            {error}
          </span>
          {/* ต้องมีทางออกให้ผู้ใช้เสมอ ไม่ใช่บอกว่าพังแล้วจบ */}
          <button
            type="button"
            onClick={() => setReloadKey((k) => k + 1)}
            className="btn shrink-0 border border-rose-300 bg-white px-3 py-1.5 text-rose-700 hover:bg-rose-100"
          >
            <RotateCcw className="h-4 w-4" aria-hidden />
            ลองใหม่
          </button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
        {/* ตารางเรียน */}
        <section className="card overflow-hidden">
          <header className="flex items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
            <h2 className="flex items-center gap-2 font-semibold text-slate-800">
              <CalendarDays className="h-5 w-5 text-brand-600" aria-hidden />
              ตารางเรียน {state.term}
            </h2>
            <span className="text-sm tabular-nums text-slate-600">
              {planned.length} วิชา · <strong className={credits > state.preferences.maxCredits ? "text-rose-600" : "text-slate-800"}>{credits}</strong> หน่วยกิต
              {checking && <Loader2 className="ml-2 inline h-3.5 w-3.5 animate-spin text-slate-400" aria-hidden />}
            </span>
          </header>

          {planned.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <CalendarDays className="mx-auto h-10 w-10 text-slate-300" aria-hidden />
              <p className="mt-3 font-medium text-slate-700">ยังไม่มีวิชาในตาราง</p>
              <p className="mt-1 text-sm text-slate-500">
                เลือกวิชาจาก<span className="lg:hidden">รายการด้านล่าง</span>
                <span className="hidden lg:inline">รายการด้านขวา</span> หรือกด
                &ldquo;ให้ระบบจัดตารางให้&rdquo;
              </p>
            </div>
          ) : (
            <Timetable
              sections={planned}
              clashingIds={clashingIds}
              onRemove={(id) => toggle(id)}
            />
          )}

          {/* คำอธิบายสี */}
          <div className="flex flex-wrap gap-3 border-t border-slate-200 px-4 py-2.5 text-[11px] text-slate-600">
            {Object.entries(CATEGORY_LABEL).map(([k, label]) => (
              <span key={k} className="flex items-center gap-1.5">
                <span className={`h-2.5 w-2.5 rounded-sm ${CATEGORY_STYLE[k].dot}`} aria-hidden />
                {label}
              </span>
            ))}
            <span className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm bg-rose-500" aria-hidden />
              ชนกัน
            </span>
          </div>
        </section>

        {/* ฝั่งขวา: ผลตรวจ + เลือกวิชา */}
        <div className="space-y-4">
          {result && (
            <section className="card p-4">
              <IssuePanel
                conflicts={result.conflicts}
                warnings={result.warnings}
                summary={result.summary}
                onApplySuggestion={applySuggestion}
              />
            </section>
          )}

          {skipped.length > 0 && (
            <section className="card p-4">
              <h3 className="text-sm font-semibold text-slate-800">วิชาที่ระบบยังไม่ได้ลงให้</h3>
              <ul className="mt-2 space-y-1 text-xs text-slate-600">
                {skipped.slice(0, 6).map((s) => (
                  <li key={s.course_code}>
                    <span className="font-mono text-slate-500">{s.course_code}</span> — {s.reason}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="card flex h-[560px] flex-col overflow-hidden">
            <header className="border-b border-slate-200 px-4 py-3">
              <h2 className="font-semibold text-slate-800">เลือกรายวิชา</h2>
            </header>
            {loading ? (
              <div className="grid flex-1 place-items-center text-sm text-slate-500">
                <span className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> กำลังโหลดรายวิชา...
                </span>
              </div>
            ) : (
              <CoursePicker
                courses={courses}
                selectedIds={state.selectedIds}
                onToggle={toggle}
                clashingIds={clashingIds}
              />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
