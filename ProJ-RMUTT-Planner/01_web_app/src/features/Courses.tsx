import { copy as uiCopy } from "@/i18n/th";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Plus,
  Search,
  Users,
} from "lucide-react";
import { useApiPage } from "@/api/queries";
import type { Course, Section } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Empty, ErrorBox, Loading } from "@/components/Common";
import { useApp } from "@/state";
import { th } from "@/i18n/th";
import { sectionNumber } from "@/lib/utils";
export function SectionsList({
  code,
  onSelect,
  selectedIds = [],
}: {
  code: string;
  onSelect: (section: Section) => void;
  selectedIds?: string[];
}) {
  const result = useApiPage<Section>(
    ["sections", code],
    `/courses/${encodeURIComponent(code)}/sections?term=1%2F2569`,
  );
  return (
    <div className="sections-list">
      <ErrorBox error={result.error} />
      {result.isLoading ? (
        <Loading />
      ) : (
        result.data?.items.map((s) => (
          <div className="section-row" key={s.section_id}>
            <span className="section-number">{sectionNumber(s.section_id)}</span>
            <div>
              <strong>Section {sectionNumber(s.section_id)}</strong>
              <small>{s.teacher}</small>
            </div>
            <div className="section-time">
              {s.meetings.map((m, i) => (
                <span key={i}>
                  {th.days[m.day]} {m.start}–{m.end}
                  <small>{m.room}</small>
                </span>
              ))}
            </div>
            <span className={s.seats_available ? "seats" : "seats full"}>
              <Users size={14} />
              {s.seats_available
                ? uiCopy.courses001 + s.seats_available + uiCopy.courses002
                : uiCopy.courses003}
            </span>
            <Button
              size="sm"
              variant={
                selectedIds.includes(s.section_id) ? "secondary" : "outline"
              }
              onClick={() => onSelect(s)}
              disabled={!s.seats_available || selectedIds.includes(s.section_id)}
              aria-label={
                uiCopy.courses004 +
                s.course_code +
                " section " +
                sectionNumber(s.section_id) +
                ""
              }
            >
              {selectedIds.includes(s.section_id) ? <Check /> : <Plus />}
              {selectedIds.includes(s.section_id)
                ? uiCopy.courses005
                : uiCopy.courses006}
            </Button>
          </div>
        ))
      )}
    </div>
  );
}
export default function Courses() {
  const { draft, setDraft, notify } = useApp(),
    [q, setQ] = useState(""),
    [debounced, setDebounced] = useState(""),
    [day, setDay] = useState(""),
    [teacher, setTeacher] = useState(""),
    [cursorStack, setCursorStack] = useState<(string | null)[]>([null]),
    [expanded, setExpanded] = useState<string | null>(null);
  const page = cursorStack.length;
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(q), 250);
    return () => clearTimeout(timer);
  }, [q]);
  const cursor = cursorStack[cursorStack.length - 1];
  const query = useApiPage<Course>(
    ["courses", debounced, day, teacher, cursor],
    // ส่งเฉพาะตัวกรองที่เลือก: 02 ตรวจ day เป็น MON..SUN ส่ง day= ว่างไปจะได้ 422
    // (เดิมหน้านี้พังตั้งแต่เปิด เพราะค่าเริ่มต้นของ day คือ "" = ทุกวัน)
    `/courses?${new URLSearchParams({
      term: "1/2569",
      ...(debounced ? { q: debounced } : {}),
      ...(day ? { day } : {}),
      ...(teacher ? { teacher } : {}),
      ...(cursor ? { cursor } : {}),
    })}`,
  );
  function add(s: Section) {
    setDraft([...draft.filter((d) => d.course_code !== s.course_code), s]);
    notify(
      uiCopy.courses007 +
        s.course_code +
        " section " +
        sectionNumber(s.section_id) +
        uiCopy.courses008,
    );
  }
  return (
    <section className="page-content">
      <div className="page-heading">
        <div>
          <span className="eyebrow">{uiCopy.courses009}</span>
          <h2>{uiCopy.courses010}</h2>
          <p>{uiCopy.courses011}</p>
        </div>
        <Button asChild>
          <Link to="/planner">
            {uiCopy.courses012}
            <span className="button-count">{draft.length}</span>
            <ArrowRight />
          </Link>
        </Button>
      </div>
      <div className="filter-bar">
        <div className="search-field">
          <Search size={19} />
          <input
            aria-label={uiCopy.courses013}
            placeholder={uiCopy.courses014}
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setCursorStack([null]);
            }}
          />
        </div>
        <select
          aria-label={uiCopy.courses015}
          value={day}
          onChange={(e) => {
            setDay(e.target.value);
            setCursorStack([null]);
          }}
        >
          <option value="">{uiCopy.courses016}</option>
          {Object.entries(th.days).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          aria-label={uiCopy.courses017}
          value={teacher}
          onChange={(e) => {
            setTeacher(e.target.value);
            setCursorStack([null]);
          }}
        >
          <option value="">{uiCopy.courses018}</option>
          {[
            uiCopy.courses019,
            uiCopy.courses020,
            uiCopy.courses021,
            uiCopy.courses022,
            uiCopy.courses023,
            uiCopy.courses024,
          ].map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <select aria-label={uiCopy.courses025}>
          <option>1/2569</option>
        </select>
      </div>
      <div className="results-heading">
        <span>{uiCopy.courses026}</span>
        <small>
          {query.data?.items.length ?? 0}
          {uiCopy.courses027}
        </small>
      </div>
      <ErrorBox error={query.error} />
      {query.isLoading ? (
        <Loading />
      ) : query.data?.items.length ? (
        <div className="courses-list">
          {query.data.items.map((c) => (
            <article className="course-card" key={c.code}>
              <button
                className="course-summary"
                aria-expanded={expanded === c.code}
                onClick={() => setExpanded(expanded === c.code ? null : c.code)}
              >
                <span className="course-icon">
                  <BookOpen size={25} />
                </span>
                <span className="course-info">
                  <span className="course-code">{c.code}</span>
                  <strong>{c.name_th}</strong>
                  <small>{c.name_en}</small>
                </span>
                <span className="credit-tag">
                  {c.credits}
                  <small>{uiCopy.courses028}</small>
                </span>
                <ChevronDown
                  size={18}
                  className={expanded === c.code ? "rotated" : ""}
                />
              </button>
              {expanded === c.code && (
                <SectionsList
                  code={c.code}
                  onSelect={add}
                  selectedIds={draft.map((s) => s.section_id)}
                />
              )}
            </article>
          ))}
        </div>
      ) : (
        <Empty icon={<Search size={36} />} title={uiCopy.courses029}>
          <p>{uiCopy.courses030}</p>
          <Button
            variant="outline"
            onClick={() => {
              setQ("");
              setDay("");
              setTeacher("");
              setCursorStack([null]);
            }}
          >
            {uiCopy.courses031}
          </Button>
        </Empty>
      )}
      <div className="pagination">
        <Button
          variant="outline"
          size="sm"
          disabled={page === 1}
          onClick={() => setCursorStack((stack) => stack.slice(0, -1))}
        >
          <ChevronLeft />
          {uiCopy.courses032}
        </Button>
        <span>
          {uiCopy.courses033}
          {page}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!query.data?.nextCursor}
          onClick={() =>
            query.data?.nextCursor &&
            setCursorStack((stack) => [...stack, query.data!.nextCursor])
          }
        >
          {uiCopy.courses034}
          <ChevronRight />
        </Button>
      </div>
    </section>
  );
}
