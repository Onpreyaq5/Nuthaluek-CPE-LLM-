"use client";

import { DAY_TH, categoryStyle, hhmm, type PlannedSection } from "../lib/types";

const START_MIN = 8 * 60;   // 08:00
const END_MIN = 21 * 60;    // 21:00
const HOURS = Array.from({ length: (END_MIN - START_MIN) / 60 }, (_, i) => START_MIN + i * 60);
const ROW_PX = 56;          // ความสูงต่อ 1 ชั่วโมง

type Block = {
  key: string;
  day: number;
  start: number;
  end: number;
  code: string;
  section: string;
  name: string;
  room: string;
  kind: string;
  category: string;
  clashing: boolean;
};

function toBlocks(sections: PlannedSection[], clashIds: Set<string>): Block[] {
  const out: Block[] = [];
  for (const s of sections) {
    for (const [i, m] of s.meetings.entries()) {
      if (m.day < 0 || m.day > 6) continue;
      out.push({
        key: `${s.id}-${i}`,
        day: m.day,
        start: m.start_min,
        end: m.end_min,
        code: s.course_code,
        section: s.section,
        name: s.course_name,
        room: m.room,
        kind: m.meeting_type === "lab" ? "ปฏิบัติ" : "บรรยาย",
        category: s.category,
        clashing: clashIds.has(s.id),
      });
    }
  }
  return out;
}

/** ตารางเรียนรายสัปดาห์ — วิชาที่ชนกันจะขึ้นกรอบแดงพร้อมไอคอนเตือน */
export function Timetable({
  sections,
  clashingIds = new Set<string>(),
  onRemove,
}: {
  sections: PlannedSection[];
  clashingIds?: Set<string>;
  onRemove?: (sectionId: string) => void;
}) {
  const blocks = toBlocks(sections, clashingIds);
  const usedDays = new Set(blocks.map((b) => b.day));
  // ซ่อนวันอาทิตย์ถ้าไม่มีเรียน จะได้ไม่เปลืองพื้นที่
  const days = [0, 1, 2, 3, 4, 5, 6].filter((d) => d !== 6 || usedDays.has(6));

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[720px]">
        {/* หัวตาราง */}
        <div
          className="grid border-b border-slate-200"
          style={{ gridTemplateColumns: `64px repeat(${days.length}, minmax(0, 1fr))` }}
        >
          <div />
          {days.map((d) => (
            <div key={d} className="px-2 py-2 text-center">
              <span className="text-sm font-semibold text-slate-700">{DAY_TH[d]}</span>
              {!usedDays.has(d) && (
                <span className="mt-0.5 block text-[11px] font-medium text-emerald-600">ว่างทั้งวัน</span>
              )}
            </div>
          ))}
        </div>

        {/* พื้นที่ตาราง */}
        <div
          className="relative grid"
          style={{
            gridTemplateColumns: `64px repeat(${days.length}, minmax(0, 1fr))`,
            height: HOURS.length * ROW_PX,
          }}
        >
          {/* แถบเวลา */}
          <div className="relative border-r border-slate-200">
            {HOURS.map((h, i) => (
              <div
                key={h}
                className="absolute right-2 -translate-y-1/2 text-[11px] tabular-nums text-slate-400"
                style={{ top: i * ROW_PX }}
              >
                {hhmm(h)}
              </div>
            ))}
          </div>

          {days.map((d) => (
            <div key={d} className="relative border-r border-slate-100 last:border-r-0">
              {HOURS.map((h, i) => (
                <div
                  key={h}
                  className="absolute inset-x-0 border-t border-slate-100"
                  style={{ top: i * ROW_PX }}
                />
              ))}

              {blocks
                .filter((b) => b.day === d)
                .map((b) => {
                  const top = ((b.start - START_MIN) / 60) * ROW_PX;
                  const height = Math.max(((b.end - b.start) / 60) * ROW_PX - 4, 28);
                  const style = categoryStyle(b.category);
                  return (
                    <div
                      key={b.key}
                      className={[
                        "absolute inset-x-1 overflow-hidden rounded-lg border px-2 py-1 shadow-sm",
                        b.clashing ? "border-rose-500 bg-rose-500/95 text-white ring-2 ring-rose-300" : style.block,
                      ].join(" ")}
                      style={{ top, height }}
                      title={`${b.code} หมู่ ${b.section} · ${b.name}\n${hhmm(b.start)}-${hhmm(b.end)} · ${b.kind} ${b.room}`}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <span className="truncate text-[11px] font-semibold leading-tight">
                          {b.clashing && <span aria-label="ชนกัน">⚠ </span>}
                          {b.code}
                        </span>
                        {onRemove && (
                          <button
                            type="button"
                            onClick={() => onRemove(`${b.code}-${b.section}`)}
                            className="shrink-0 rounded px-1 text-[11px] leading-none opacity-70 hover:bg-black/20 hover:opacity-100"
                            aria-label={`เอา ${b.code} หมู่ ${b.section} ออก`}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                      <div className="truncate text-[10px] leading-tight opacity-90">
                        ม.{b.section} · {hhmm(b.start)}-{hhmm(b.end)}
                      </div>
                      {height > 44 && (
                        <div className="truncate text-[10px] leading-tight opacity-80">
                          {b.kind} {b.room}
                        </div>
                      )}
                    </div>
                  );
                })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
