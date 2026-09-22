// ตัวเรียก API — จุดเดียวที่คุยกับฟังก์ชัน Python
import type { AutoPlanResult, ChatResult, CoursesResult, ValidateResult } from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const text = await res.text();
  let data: unknown;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`เซิร์ฟเวอร์ตอบกลับไม่ใช่ JSON (${res.status})`);
  }
  if (!res.ok) {
    const msg = (data as { error?: { message?: string } })?.error?.message;
    throw new Error(msg || `เรียก ${path} ไม่สำเร็จ (${res.status})`);
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
