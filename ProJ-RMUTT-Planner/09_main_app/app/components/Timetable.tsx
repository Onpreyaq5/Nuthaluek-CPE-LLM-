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
  lane: number;    // คอลัมน์ย่อยที่ 0..lanes-1 เมื่อมีคาบทับกัน
  lanes: number;   // จำนวนคอลัมน์ย่อยในกลุ่มที่ทับกัน
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
        lane: 0,
        lanes: 1,
      });
    }
  }
  return assignLanes(out);
}

/** แบ่งคอลัมน์ย่อยให้คาบที่เวลาทับกัน
 *
 * ถ้าไม่ทำ บล็อกที่ชนกันจะวางทับกันสนิทจนเห็นแค่อันบนสุด
 * ซึ่งขัดกับหน้าที่หลักของหน้านี้ คือทำให้ผู้ใช้เห็นว่าวิชาไหนชนกับวิชาไหน
 */
function assignLanes(blocks: Block[]): Block[] {
  for (let day = 0; day <= 6; day++) {
    const ofDay = blocks.filter((b) => b.day === day).sort((a, b) => a.start - b.start || a.end - b.end);

    // จับกลุ่มคาบที่เวลาต่อเนื่องทับกัน แล้วแบ่งคอลัมน์ภายในกลุ่ม
    let group: Block[] = [];
    let groupEnd = -1;

    const flush = () => {
      if (group.length === 0) return;
      const laneEnds: number[] = [];
      for (const b of group) {
        let lane = laneEnds.findIndex((end) => end <= b.start);
        if (lane === -1) {
          lane = laneEnds.length;
          laneEnds.push(b.end);
        } else {
          laneEnds[lane] = b.end;
        }
        b.lane = lane;
      }
      for (const b of group) b.lanes = laneEnds.length;
      group = [];
      groupEnd = -1;
    };

    for (const b of ofDay) {
      if (group.length > 0 && b.start >= groupEnd) flush();
      group.push(b);
      groupEnd = Math.max(groupEnd, b.end);
    }
    flush();
  }
  return blocks;
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
    <>
      {/* จอมือถือ: ตารางกริดกว้าง 720px ต้องเลื่อนแนวนอน ซึ่งผู้ใช้ส่วนใหญ่ไม่รู้ว่าเลื่อนได้
          จะเห็นแต่ช่องว่างของวันจันทร์-พุธ แล้วนึกว่าแผนยังไม่มีอะไร จึงแสดงเป็นรายวันแทน */}
      <div className="divide-y divide-slate-100 sm:hidden">
        {days.map((d) => {
          const ofDay = blocks.filter((b) => b.day === d).sort((a, b) => a.start - b.start);
          if (ofDay.length === 0) {
            return (
              <div key={d} className="flex items-center justify-between px-4 py-2.5">
                <span className="text-sm font-medium text-slate-500">{DAY_TH[d]}</span>
                <span className="text-xs font-medium text-emerald-600">ว่างทั้งวัน</span>
              </div>
            );
          }
          return (
            <div key={d} className="px-4 py-3">
              <p className="text-sm font-semibold text-slate-800">{DAY_TH[d]}</p>
              <ul className="mt-2 space-y-2">
                {ofDay.map((b) => {
                  const style = categoryStyle(b.category);
                  return (
                    <li
                      key={b.key}
                      className={[
                        "flex items-start gap-2 rounded-lg border px-3 py-2",
                        b.clashing ? "border-rose-300 bg-rose-50" : "border-slate-200 bg-white",
                      ].join(" ")}
                    >
                      <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${style.dot}`} aria-hidden />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-medium text-slate-900">
                          {b.clashing && <span className="text-rose-600">⚠ </span>}
                          {b.code} <span className="font-normal text-slate-500">ม.{b.section}</span>
                        </span>
                        <span className="block truncate text-xs text-slate-600">{b.name}</span>
                        <span className="block text-xs tabular-nums text-slate-500">
                          {hhmm(b.start)}-{hhmm(b.end)} · {b.kind} {b.room}
                        </span>
                      </span>
                      {onRemove && (
                        <button
                          type="button"
                          onClick={() => onRemove(`${b.code}-${b.section}`)}
                          className="shrink-0 rounded px-2 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                          aria-label={`เอา ${b.code} หมู่ ${b.section} ออก`}
                        >
                          ✕
                        </button>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>

      {/* จอใหญ่: ตารางกริดรายสัปดาห์ */}
      <div className="hidden overflow-x-auto sm:block">
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
                <span className="mt-0.5 block text-[11px] font-medium text-emerald-600">ว่าง</span>
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
                  // คาบที่ทับกันวางเหลื่อมกันแทนการหารความกว้างเท่า ๆ กัน
                  // เพราะหารครึ่งแล้วบล็อกแคบจนอ่านตัวหนังสือไม่ออก
                  // เหลื่อมทีละ 22% ทำให้เห็นครบทุกอันและยังกว้างพอจะอ่านได้
                  const STAGGER = 22;
                  const width = 100 - (b.lanes - 1) * STAGGER;
                  const left = b.lane * STAGGER;
                  return (
                    <div
                      key={b.key}
                      className={[
                        "absolute overflow-hidden rounded-lg border px-2 py-1 shadow-sm",
                        b.clashing ? "border-rose-500 bg-rose-500/95 text-white ring-2 ring-rose-300" : style.block,
                      ].join(" ")}
                      style={{
                        top,
                        height,
                        left: `calc(${left}% + 4px)`,
                        width: `calc(${width}% - 8px)`,
                        zIndex: 10 + b.lane,
                      }}
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
    </>
  );
}
