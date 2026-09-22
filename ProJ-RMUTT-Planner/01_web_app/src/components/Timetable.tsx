import { copy as uiCopy } from "@/i18n/th";
import { AlertTriangle, CalendarDays } from "lucide-react";
import type { Section, Validation, Day } from "@/api/types";
import { th } from "@/i18n/th";
import { sectionNumber } from "@/lib/utils";
export const days: Day[] = ["MON", "TUE", "WED", "THU", "FRI", "SAT"];
export function minute(time: string) {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}
export function placement(start: string, end: string) {
  return {
    top: ((minute(start) - 480) / 720) * 100,
    height: ((minute(end) - minute(start)) / 720) * 100,
  };
}
export function Timetable({
  sections,
  validation,
  onSelect,
  compact = false,
}: {
  sections: Section[];
  validation?: Validation;
  onSelect?: (section: Section) => void;
  compact?: boolean;
}) {
  const conflicting = new Set(
    validation?.conflicts?.flatMap((c) => c.section_ids ?? []) || [],
  );
  return (
    <div className={`timetable-wrap ${compact ? "compact" : ""}`}>
      <div className="timetable-desktop">
        <div className="timetable-head">
          <span>
            <CalendarDays size={17} />
          </span>
          {days.map((d) => (
            <strong key={d}>{th.days[d]}</strong>
          ))}
        </div>
        <div className="timetable-grid">
          <div className="time-axis">
            {Array.from({ length: 13 }, (_, i) => (
              <span key={i} style={{ top: `${(i / 12) * 100}%` }}>
                {String(i + 8).padStart(2, "0")}:00
              </span>
            ))}
          </div>
          {days.map((day) => (
            <div className="day-column" key={day}>
              {sections.flatMap((section, index) =>
                section.meetings
                  .filter((m) => m.day === day)
                  .map((meeting, i) => {
                    const bounds = placement(meeting.start, meeting.end),
                      conflict = conflicting.has(section.section_id);
                    return (
                      <button
                        type="button"
                        key={`${section.section_id}-${i}`}
                        className={`class-block color-${index % 5} ${conflict ? "conflict" : ""}`}
                        style={{
                          top: `${bounds.top}%`,
                          height: `${bounds.height}%`,
                          ...(conflict
                            ? {
                                width: "calc(50% - 5px)",
                                left: index % 2 ? "50%" : "4px",
                              }
                            : {}),
                        }}
                        onClick={() => onSelect?.(section)}
                        disabled={!onSelect}
                        aria-label={
                          "" +
                          section.course_code +
                          " section " +
                          sectionNumber(section.section_id) +
                          " " +
                          th.days[day] +
                          " " +
                          meeting.start +
                          uiCopy.timetable001 +
                          meeting.end +
                          "" +
                          (conflict ? " เวลาชน" : "") +
                          ""
                        }
                      >
                        <strong>
                          {section.course_code}
                          {conflict && <AlertTriangle size={13} />}
                        </strong>
                        <span>{section.course_name_th}</span>
                        <small>
                          {meeting.start}–{meeting.end}
                        </small>
                        <small>
                          Sec {sectionNumber(section.section_id)} • {meeting.room}
                        </small>
                      </button>
                    );
                  }),
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="timetable-mobile">
        {days.map((day) => {
          const list = sections
            .flatMap((s) =>
              s.meetings.filter((m) => m.day === day).map((m) => ({ s, m })),
            )
            .sort((a, b) => a.m.start.localeCompare(b.m.start));
          return (
            <div key={day}>
              <h4>{th.days[day]}</h4>
              {list.length ? (
                list.map(({ s, m }) => (
                  <button
                    key={s.section_id}
                    className={
                      conflicting.has(s.section_id)
                        ? "mobile-class conflict"
                        : "mobile-class"
                    }
                    onClick={() => onSelect?.(s)}
                    disabled={!onSelect}
                  >
                    <strong>
                      {m.start}–{m.end}
                    </strong>
                    <span>
                      {s.course_code} • {s.course_name_th}
                      <small>
                        Sec {sectionNumber(s.section_id)} • {m.room}
                      </small>
                    </span>
                    {conflicting.has(s.section_id) && <AlertTriangle size={17} />}
                  </button>
                ))
              ) : (
                <p>{uiCopy.timetable002}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
