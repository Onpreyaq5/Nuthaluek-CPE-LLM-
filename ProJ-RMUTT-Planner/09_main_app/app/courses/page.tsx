"use client";

import { useEffect, useMemo, useState } from "react";
import { BookOpen, Loader2, Search, Users } from "lucide-react";
import { api } from "../lib/api";
import { CATEGORY_LABEL, DAY_TH, categoryStyle, hhmm, type Course } from "../lib/types";

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [terms, setTerms] = useState<string[]>([]);
  const [term, setTerm] = useState("1/2569");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .courses({ term })
      .then((d) => {
        if (cancelled) return;
        setCourses(d.courses);
        setTerms(d.available_terms);
      })
      .catch((e: Error) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [term]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return courses;
    return courses.filter(
      (c) => c.course_code.toLowerCase().includes(s) || c.course_name.toLowerCase().includes(s),
    );
  }, [courses, q]);

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h1 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
          <BookOpen className="h-5 w-5 text-brand-600" aria-hidden />
          รายวิชาที่เปิดสอน
        </h1>
        <div className="mt-3 flex flex-wrap gap-3">
          <div className="relative min-w-[240px] flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              aria-hidden
            />
            <input
              className="input pl-9"
              placeholder="ค้นรหัสวิชา หรือชื่อวิชา"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="ค้นหารายวิชา"
            />
          </div>
          <select
            className="input w-40"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            aria-label="ภาคการศึกษา"
          >
            {(terms.length ? terms : [term]).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <p className="mt-2 text-sm text-slate-500">พบ {filtered.length} รายวิชา</p>
      </div>

      {error && <div className="card border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}

      {loading ? (
        <div className="card grid place-items-center p-12 text-sm text-slate-500">
          <span className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> กำลังโหลด...
          </span>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {filtered.map((c) => {
            const style = categoryStyle(c.category);
            return (
              <article key={c.course_code} className="card p-4">
                <header className="flex items-start gap-2">
                  <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${style.dot}`} aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-xs text-slate-500">{c.course_code}</p>
                    <h2 className="font-semibold text-slate-900">{c.course_name}</h2>
                    <p className="mt-0.5 flex flex-wrap gap-1.5 text-xs">
                      <span className={`chip ${style.chip}`}>
                        {CATEGORY_LABEL[c.category] ?? c.category}
                      </span>
                      <span className="chip border-slate-200 bg-slate-50 text-slate-600">
                        {c.credits} หน่วยกิต
                      </span>
                      {c.suggested_year && (
                        <span className="chip border-slate-200 bg-slate-50 text-slate-600">
                          แนะนำปี {c.suggested_year}
                        </span>
                      )}
                    </p>
                    {c.prerequisites.length > 0 && (
                      <p className="mt-1.5 text-xs text-amber-700">
                        ต้องผ่าน {c.prerequisites.join(", ")} ก่อน
                      </p>
                    )}
                  </div>
                </header>

                <table className="mt-3 w-full text-xs">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="pb-1 font-medium">หมู่</th>
                      <th className="pb-1 font-medium">วัน–เวลา</th>
                      <th className="pb-1 text-right font-medium">ที่นั่ง</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {c.sections.map((s) => {
                      const full = s.seat_left !== null && s.seat_left <= 0;
                      return (
                        <tr key={s.id}>
                          <td className="py-1.5 align-top font-medium text-slate-700">{s.section}</td>
                          <td className="py-1.5 text-slate-600">
                            {s.meetings.map((m, i) => (
                              <span key={i} className="block">
                                {DAY_TH[m.day]} {hhmm(m.start_min)}-{hhmm(m.end_min)}
                                <span className="text-slate-400"> · {m.room}</span>
                              </span>
                            ))}
                          </td>
                          <td
                            className={`py-1.5 text-right align-top tabular-nums ${full ? "text-rose-600" : "text-slate-600"}`}
                          >
                            <span className="inline-flex items-center gap-1">
                              <Users className="h-3 w-3" aria-hidden />
                              {full ? "เต็ม" : s.seat_left}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
