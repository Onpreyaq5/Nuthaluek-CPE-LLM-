// ตัวเรียก API — จุดเดียวที่คุยกับฟังก์ชัน Python
import type { AutoPlanResult, ChatResult, CoursesResult, ValidateResult } from "./types";

/** กันหน้าค้างตลอดกาลเมื่อฟังก์ชันฝั่งเซิร์ฟเวอร์แฮงก์
 *  (Vercel ตัดที่ 10 วินาทีอยู่แล้ว เผื่อไว้อีกนิดให้ตอบก่อน) */
const TIMEOUT_MS = 20_000;

/** ข้อความที่ผู้ใช้อ่านแล้วรู้ว่าต้องทำอะไรต่อ ไม่ใช่ศัพท์ของโปรแกรมเมอร์ */
function friendlyStatus(status: number): string {
  if (status === 404) return "ไม่พบข้อมูลที่ขอ ลองเปลี่ยนภาคการศึกษาแล้วลองใหม่";
  if (status === 429) return "มีคนใช้งานพร้อมกันเยอะ รอสักครู่แล้วลองใหม่";
  if (status >= 500) return "ระบบขัดข้องชั่วคราว ลองกดใหม่อีกครั้งในอีกสักครู่";
  return "ส่งคำขอไม่สำเร็จ ลองใหม่อีกครั้ง";
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (e) {
    // fetch โยน error เมื่อเน็ตหลุดหรือเซิร์ฟเวอร์ไม่ตอบ — ข้อความดิบอ่านไม่รู้เรื่อง
    // ("Failed to fetch") จึงแปลงเป็นภาษาที่ผู้ใช้ทำอะไรต่อได้
    if ((e as Error).name === "TimeoutError") {
      throw new Error("เซิร์ฟเวอร์ตอบช้าผิดปกติ ลองใหม่อีกครั้ง");
    }
    if (typeof navigator !== "undefined" && navigator.onLine === false) {
      throw new Error("ไม่ได้เชื่อมต่ออินเทอร์เน็ต ต่อเน็ตแล้วลองใหม่อีกครั้ง");
    }
    throw new Error("ติดต่อเซิร์ฟเวอร์ไม่ได้ ตรวจสอบอินเทอร์เน็ตแล้วลองใหม่อีกครั้ง");
  }

  const text = await res.text();
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    // ตอบกลับเป็น HTML เกือบทุกครั้งแปลว่าเซิร์ฟเวอร์พัง ไม่ใช่ความผิดผู้ใช้
    throw new Error(friendlyStatus(res.status));
  }
  if (!res.ok) {
    const msg = (data as { error?: { message?: string } })?.error?.message;
    throw new Error(msg || friendlyStatus(res.status));
  }
  return data as T;
}

export const api = {
  courses: (params: { term?: string; q?: string; year?: number; day?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.term) qs.set("term", params.term);
    if (params.q) qs.set("q", params.q);
    if (params.year != null) qs.set("year", String(params.year));
    if (params.day != null) qs.set("day", String(params.day));
    return req<CoursesResult>(`/api/courses?${qs}`);
  },

  validate: (body: { term: string; section_ids: string[]; passed_courses?: string[] }) =>
    req<ValidateResult>("/api/validate", { method: "POST", body: JSON.stringify(body) }),

  autoplan: (body: {
    term: string;
    student_year?: number;
    passed_courses?: string[];
    retake_courses?: string[];
    locked_section_ids?: string[];
    preferences?: {
      avoid_morning?: boolean;
      free_days?: string[];
      min_credits?: number;
      max_credits?: number;
    };
  }) => req<AutoPlanResult>("/api/autoplan", { method: "POST", body: JSON.stringify(body) }),

  chat: (body: { question: string; context?: Record<string, unknown> }) =>
    req<ChatResult>("/api/chat", { method: "POST", body: JSON.stringify(body) }),

  chatStatus: () =>
    req<{ ok: boolean; knowledge: { chunks: number; files: string[] }; llm: string }>("/api/chat"),
};
