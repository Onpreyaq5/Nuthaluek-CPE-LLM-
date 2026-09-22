import { http, HttpResponse, delay } from "msw";
import {
  courses,
  sections,
  student,
  sources,
  transcript,
  leaveAnswer,
} from "./fixtures";
import type {
  ChatMessage,
  ChatRequest,
  ChatSessionSummary,
  ConflictItem,
  GeneratedPlan,
  Section,
  Validation,
  WarningItem,
} from "@/api/types";
const BASE = "/api/v1",
  DATA = "campusmate-demo-v2-data",
  AUTH = "campusmate-demo-session";
type StoredPlan = {
  id: number;
  term: string;
  name: string;
  sections: Section[];
  updated_at: string;
};
type State = {
  plans: StoredPlan[];
  sessions: ChatSessionSummary[];
  messages: Record<number, ChatMessage[]>;
  imported: boolean;
  feedback: unknown[];
  next: number;
};
const date = () => new Date().toISOString();
function seed(): State {
  const time = date();
  return {
    plans: [
      {
        id: 1,
        name: "แผนเริ่มต้นของฉัน",
        term: "1/2569",
        sections: sections.filter((s) =>
          ["CPE201-01", "CPE203-02", "CPE301-01"].includes(s.section_id),
        ),
        updated_at: time,
      },
    ],
    sessions: [
      { id: 1, title: "ขั้นตอนการลาพักการศึกษา", updated_at: time },
    ],
    messages: {
      1: [
        {
          id: 1,
          role: "user",
          content:
            "ถ้าต้องการลาพักการศึกษา ต้องเริ่มอย่างไร และใช้เอกสารอะไรบ้าง?",
          created_at: time,
          sources: [],
          status: "complete",
        },
        {
          id: 2,
          role: "assistant",
          content: leaveAnswer,
          created_at: time,
          sources,
          status: "complete",
        },
      ],
    },
    imported: false,
    feedback: [],
    next: 100,
  };
}
let state: State = seed();
try {
  const saved = JSON.parse(localStorage.getItem(DATA) || "null");
  if (
    saved?.plans &&
    saved?.sessions &&
    saved?.messages &&
    typeof saved.next === "number"
  )
    state = saved;
} catch {
  /* Fresh synthetic data. */
}
const save = () => {
  try {
    localStorage.setItem(DATA, JSON.stringify(state));
  } catch {
    /* Tab-local state remains available. */
  }
};
let authenticated = sessionStorage.getItem(AUTH) === "active";
const ok = (data: unknown) =>
  HttpResponse.json({
    ok: true,
    data,
    meta: { request_id: crypto.randomUUID(), took_ms: 35 },
  });
const fail = (status: number, code: string, message: string) =>
  HttpResponse.json(
    {
      ok: false,
      error: { code, message, details: {} },
      meta: { request_id: crypto.randomUUID(), took_ms: 0 },
    },
    { status },
  );
const auth = () =>
  authenticated
    ? null
    : fail(401, "AUTH_401", "เซสชันหมดอายุ กรุณาเข้าสู่ระบบอีกครั้ง");
const selected = (ids: string[]) =>
  sections.filter((s) => ids.includes(s.section_id));
const totalCredits = (list: Section[]) =>
  list.reduce((sum, s) => sum + s.credits, 0);
export function validate(ids: string[]): Validation {
  const list = selected(ids),
    conflicts: ConflictItem[] = [],
    warnings: WarningItem[] = [];
  for (let a = 0; a < list.length; a++)
    for (let b = a + 1; b < list.length; b++) {
      if (
        list[a].meetings.some((x) =>
          list[b].meetings.some(
            (y) => x.day === y.day && x.start < y.end && y.start < x.end,
          ),
        )
      )
        conflicts.push({
          type: "time_clash",
          message: `${list[a].course_code} และ ${list[b].course_code} มีเวลาเรียนทับซ้อนกัน กรุณาเลือก section อื่น`,
          section_ids: [list[a].section_id, list[b].section_id],
        });
      if (list[a].course_code === list[b].course_code)
        conflicts.push({
          type: "duplicate",
          message: "เลือกมากกว่าหนึ่ง section ในรายวิชาเดียวกัน",
          section_ids: [list[a].section_id, list[b].section_id],
        });
    }
  const credits = totalCredits(list);
  if (credits > 21)
    warnings.push({ type: "credit_limit", message: "จำนวนหน่วยกิตเกินเกณฑ์สาธิต 21 หน่วยกิต" });
  for (const s of list.filter((s) => s.seats_available === 0))
    warnings.push({
      type: "seat_full",
      message: `${s.course_code} ที่นั่งเต็ม`,
    });
  return {
    conflicts,
    warnings,
    summary: {
      total_credits: credits,
      section_count: list.length,
      is_valid: conflicts.length === 0,
    },
  };
}
export const handlers = [
  http.post(`${BASE}/auth/login`, async ({ request }) => {
    await delay(350);
    const body = (await request.json()) as {
      username: string;
      password: string;
    };
    if (body.username === "admin" && body.password === "admin1234") {
      authenticated = true;
      sessionStorage.setItem(AUTH, "active");
      return ok(student);
    }
    return fail(401, "AUTH_401", "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง");
  }),
  http.get(`${BASE}/auth/me`, () => auth() || ok(student)),
  http.post(`${BASE}/auth/logout`, () => {
    authenticated = false;
    sessionStorage.removeItem(AUTH);
    return ok({ logged_out: true });
  }),
  http.post(`${BASE}/demo/expire`, () => {
    authenticated = false;
    sessionStorage.removeItem(AUTH);
    return fail(401, "AUTH_401", "เซสชันตัวอย่างหมดอายุแล้ว");
  }),
  http.get(`${BASE}/courses`, async ({ request }) => {
    const denied = auth();
    if (denied) return denied;
    await delay(180);
    const p = new URL(request.url).searchParams,
      q = (p.get("q") || "").toLowerCase(),
      day = p.get("day"),
      teacher = p.get("teacher"),
      cursor = Number(p.get("cursor") || 0),
      pageSize = 4;
    const all = courses.filter(
      (c) =>
        `${c.name_th} ${c.name_en} ${c.code}`.toLowerCase().includes(q) &&
        (!day ||
          sections.some((s) => s.course_code === c.code && s.meetings.some((m) => m.day === day))) &&
        (!teacher ||
          sections.some((s) => s.course_code === c.code && s.teacher.includes(teacher))),
    );
    const items = all.slice(cursor, cursor + pageSize);
    const nextCursor = cursor + pageSize < all.length ? String(cursor + pageSize) : null;
    return ok({ items, next_cursor: nextCursor });
  }),
  http.get(`${BASE}/courses/:code/sections`, async ({ params }) => {
    const denied = auth();
    if (denied) return denied;
    await delay(100);
    const items = sections.filter((s) => s.course_code === params.code);
    return items.length
      ? ok({ items, next_cursor: null })
      : fail(404, "NOT_FOUND_404", "ไม่พบรายวิชานี้");
  }),
  http.post(`${BASE}/plans/validate`, async ({ request }) => {
    const denied = auth();
    if (denied) return denied;
    await delay(180);
    return ok(
      validate(
        ((await request.json()) as { section_ids: string[] }).section_ids,
      ),
    );
  }),
  http.get(`${BASE}/plans`, () =>
    auth() ||
    ok({
      items: state.plans.map((p) => ({
        id: p.id,
        term: p.term,
        name: p.name,
        total_credits: totalCredits(p.sections),
        updated_at: p.updated_at,
      })),
      next_cursor: null,
    }),
  ),
  http.post(`${BASE}/plans`, async ({ request }) => {
    const denied = auth();
    if (denied) return denied;
    const b = (await request.json()) as {
      name: string;
      term: string;
      section_ids: string[];
    };
    if (!b.name?.trim() || !b.section_ids.length)
      return fail(
        422,
        "VALIDATION_422",
        "ระบุชื่อแผนและเลือกอย่างน้อยหนึ่งรายวิชา",
      );
    if (state.plans.some((p) => p.name === b.name.trim()))
      return fail(409, "CONFLICT_409", "ชื่อแผนนี้มีอยู่แล้ว กรุณาใช้ชื่ออื่น");
    if (!validate(b.section_ids).summary.is_valid)
      return fail(
        422,
        "VALIDATION_422",
        "แผนนี้ยังมีข้อขัดแย้ง กรุณาปรับก่อนบันทึก",
      );
    const p: StoredPlan = {
      id: state.next++,
      term: b.term,
      name: b.name.trim(),
      sections: selected(b.section_ids),
      updated_at: date(),
    };
    state.plans.unshift(p);
    save();
    return ok({ plan_id: p.id });
  }),
  http.post(`${BASE}/plans/auto`, async ({ request }) => {
    const denied = auth();
    if (denied) return denied;
    await delay(1000);
    const b = (await request.json()) as {
      preferences: {
        free_days: string[];
        no_early_class: boolean;
        max_credits: number;
      };
      must_include: string[];
    };
    const combos = [
      ["CPE201-01", "CPE203-02", "CPE301-01", "MAT201-01", "ENG201-01"],
      ["CPE201-02", "CPE203-02", "CPE301-01", "MAT201-02", "ENG201-01"],
      ["CPE201-01", "CPE203-02", "CPE301-01", "MAT201-01", "CPE204-02"],
      ["CPE201-02", "CPE203-02", "CPE301-01", "MAT201-01", "ENG201-02"],
    ];
    const explanations = [
      "กระจายวิชาเรียนและเว้นวันศุกร์",
      "จัดวิชาช่วงบ่ายและกระจายภาระการเรียน",
      "เพิ่มวิชาเครือข่ายแทนภาษาอังกฤษ",
      "ทางเลือกสำหรับผู้ที่สะดวกเรียนวันเสาร์",
    ];
    const plans: GeneratedPlan[] = combos
      .map((ids, i) => {
        const list = selected(ids),
          v = validate(ids);
        return {
          sections: ids,
          total_credits: v.summary.total_credits,
          relaxed_constraints: [],
          explanation: explanations[i],
          warnings: (v.warnings ?? []).map((w) => w.message),
          __list: list,
          __valid: v.summary.is_valid,
        };
      })
      .filter(
        (p) =>
          p.__valid &&
          p.total_credits <= b.preferences.max_credits &&
          b.must_include.every((id) => p.sections.includes(id)) &&
          p.__list.every((s) =>
            s.meetings.every(
              (m) =>
                !b.preferences.free_days.includes(m.day) &&
                (!b.preferences.no_early_class || m.start >= "09:00"),
            ),
          ),
      )
      .slice(0, 3)
      .map(({ __list, __valid, ...rest }) => rest);
    return ok({ plans });
  }),
  http.get(`${BASE}/plans/:id/explain`, ({ params }) => {
    const denied = auth();
    if (denied) return denied;
    const p = state.plans.find((p) => p.id === Number(params.id));
    return p
      ? ok({
          explanation: `แผน "${p.name}" ประกอบด้วย ${p.sections.length} วิชา ผ่านการตรวจเวลาทับซ้อนจากบริการจำลองแล้ว แต่ยังไม่ได้ตรวจเงื่อนไขหลักสูตรจริง ควรปรึกษาอาจารย์ที่ปรึกษาก่อนลงทะเบียน`,
          sources,
        })
      : fail(404, "NOT_FOUND_404", "ไม่พบแผนนี้");
  }),
  http.get(`${BASE}/plans/:id`, ({ params }) => {
    const denied = auth();
    if (denied) return denied;
    const p = state.plans.find((p) => p.id === Number(params.id));
    return p ? ok(p) : fail(404, "NOT_FOUND_404", "ไม่พบแผนนี้");
  }),
  http.delete(`${BASE}/plans/:id`, ({ params }) => {
    const denied = auth();
    if (denied) return denied;
    if (!state.plans.some((p) => p.id === Number(params.id)))
      return fail(404, "NOT_FOUND_404", "ไม่พบแผนนี้");
    state.plans = state.plans.filter((p) => p.id !== Number(params.id));
    save();
    return ok({ deleted: true });
  }),
  http.get(`${BASE}/students/me/profile`, () => auth() || ok(student)),
  http.get(`${BASE}/students/me/transcript`, () => {
    const denied = auth();
    if (denied) return denied;
    const courses = state.imported ? transcript : [];
    return ok({
      courses,
      credits_by_category: state.imported
        ? { ทั่วไป: courses.reduce((sum, c) => sum + c.credits, 0) }
        : {},
    });
  }),
  http.post(`${BASE}/students/me/import`, async ({ request }) => {
    const denied = auth();
    if (denied) return denied;
    const f = (await request.formData()).get("file");
    if (!(f instanceof File) || !f.name.toLowerCase().endsWith(".html"))
      return fail(422, "VALIDATION_422", "กรุณาเลือกไฟล์ .html");
    if (f.size > 2 * 1024 * 1024)
      return fail(413, "FILE_TOO_LARGE_413", "ไฟล์ต้องมีขนาดไม่เกิน 2 MB");
    if (!(await f.text()).includes("campusmate-demo-transcript"))
      return fail(
        422,
        "VALIDATION_422",
        "โหมดจำลองรองรับเฉพาะไฟล์ตัวอย่างที่ดาวน์โหลดจากหน้านี้",
      );
    await delay(400);
    state.imported = true;
    save();
    return ok({
      imported_courses: transcript.length,
      retake_required: ["PHY101"],
      credits_remaining: student.credits_remaining,
      warnings: ["ข้อมูลนี้เป็นตัวอย่าง ไม่ใช่ผลการเรียนจริง"],
    });
  }),
  http.post(`${BASE}/feedback`, async ({ request }) => {
    const denied = auth();
    if (denied) return denied;
    state.feedback.push(await request.json());
    save();
    return ok({ feedback_id: state.next++ });
  }),
  http.get(`${BASE}/chat/sessions`, () =>
    auth() ||
    ok({
      items: [...state.sessions].sort((a, b) =>
        b.updated_at.localeCompare(a.updated_at),
      ),
      next_cursor: null,
    }),
  ),
  http.get(`${BASE}/chat/sessions/:id/messages`, ({ params }) =>
    auth() ||
    (state.messages[Number(params.id)]
      ? ok({ items: state.messages[Number(params.id)], next_cursor: null })
      : fail(404, "NOT_FOUND_404", "ไม่พบบทสนทนานี้")),
  ),
  http.post(`${BASE}/chat`, async ({ request }) => {
    const denied = auth();
    if (denied) return denied;
    const b = (await request.json()) as ChatRequest & {
      plan_draft?: { term: string; section_ids: string[] } | null;
    };
    if (!b.message?.trim())
      return fail(422, "VALIDATION_422", "กรุณาพิมพ์ข้อความ");
    if (b.message === "ทดสอบ 502")
      return fail(502, "UPSTREAM_502", "บริการปลายทางจำลองไม่พร้อมใช้งาน");
    const sid = b.session_id ?? state.next++;
    if (b.session_id && !state.messages[sid])
      return fail(404, "NOT_FOUND_404", "ไม่พบบทสนทนา");
    if (!state.messages[sid]) {
      state.sessions.unshift({
        id: sid,
        title: b.message.slice(0, 46),
        updated_at: date(),
      });
      state.messages[sid] = [];
    }
    const mid = state.next++;
    state.messages[sid].push({
      id: state.next++,
      role: "user",
      content: b.message,
      created_at: date(),
      sources: [],
      status: "complete",
    });
    save();
    let answer = leaveAnswer;
    if (b.plan_draft?.section_ids.length)
      answer = `แผนร่างของคุณมี ${b.plan_draft.section_ids.length} section ครับ\n\nหน้าจัดตารางเรียนจะตรวจแผนให้อัตโนมัติ เพื่อแสดงเวลาทับซ้อนและคำเตือนจากบริการตรวจแผน\n\nนี่เป็นคำตอบจำลอง ยังไม่ได้ประเมินเงื่อนไขหลักสูตรจริง`;
    else if (/ลงทะเบียน|เอกสาร|สรุป/.test(b.message))
      answer =
        "ก่อนลงทะเบียน แนะนำให้ตรวจสอบรายการต่อไปนี้ครับ\n\n1. รายวิชาและ section ที่เปิดสอนในภาคเรียน\n2. เงื่อนไขวิชาบังคับก่อนและหน่วยกิต\n3. เวลาเรียนและเวลาสอบที่อาจทับซ้อน\n\nเริ่มเลือกวิชาได้ที่เมนู 'ค้นหารายวิชา' แล้วให้ระบบช่วยตรวจแผนของคุณ";
    else if (/ติดต่อ/.test(b.message))
      answer =
        "ติดต่อหน่วยงานทะเบียนหรือเจ้าหน้าที่ประจำคณะครับ\n\nตรวจสอบช่องทางจากเว็บไซต์อย่างเป็นทางการ ตัวอย่างนี้ไม่มีเบอร์โทรหรืออีเมลที่ยืนยันแล้ว จึงไม่สร้างข้อมูลติดต่อขึ้นมา";
    else if (!/ลา|ระเบียบ|ทดสอบ/.test(b.message))
      answer =
        "ยินดีช่วยครับ! คุณสามารถถามเกี่ยวกับระเบียบการศึกษา หรือเลือกวิชาเพื่อจัดแผนลงทะเบียนได้\n\nเว็บนี้ใช้คำตอบและข้อมูลจำลอง เมื่อทีมเชื่อม Backend แล้วจะตอบจากข้อมูลมหาวิทยาลัยจริง";
    let partial = "",
      finished = false,
      cancelled = false;
    const persist = (status: ChatMessage["status"], withSources = false) => {
      if (finished) return;
      finished = true;
      state.messages[sid].push({
        id: mid,
        role: "assistant",
        content: partial,
        created_at: date(),
        sources: withSources ? sources : [],
        status,
      });
      const session = state.sessions.find((s) => s.id === sid);
      if (session) session.updated_at = date();
      save();
    };
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      async start(controller) {
        const emit = (event: unknown) => {
          if (cancelled) return;
          const bytes = encoder.encode(`data: ${JSON.stringify(event)}\n\n`),
            split = Math.max(1, Math.floor(bytes.length / 2));
          controller.enqueue(bytes.slice(0, split));
          controller.enqueue(bytes.slice(split));
        };
        try {
          emit({ type: "session", session_id: sid });
          emit({ type: "tool_start", tool: "search_knowledge" });
          await delay(380);
          if (cancelled) return;
          emit({ type: "tool_end", tool: "search_knowledge" });
          const tokens = Array.from(answer);
          for (let i = 0; i < tokens.length; i += 9) {
            await delay(28);
            if (cancelled) return;
            const text = tokens.slice(i, i + 9).join("");
            partial += text;
            emit({ type: "token", text });
            if (i > 54 && b.message === "ทดสอบ stream ขาด") {
              persist("interrupted");
              controller.close();
              return;
            }
            if (i > 54 && b.message === "ทดสอบ stream error") {
              emit({
                type: "error",
                code: "UPSTREAM_502",
                message: "บริการจำลองหยุดทำงานระหว่างตอบ",
              });
              persist("interrupted");
              controller.close();
              return;
            }
          }
          emit({ type: "sources", items: sources });
          persist("complete", true);
          emit({ type: "done", message_id: mid });
          controller.close();
        } catch {
          persist(cancelled ? "cancelled" : "interrupted");
        }
      },
      cancel() {
        cancelled = true;
        persist("cancelled");
      },
    });
    return new HttpResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  }),
];
