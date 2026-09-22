// ชนิดข้อมูลที่ใช้ร่วมกันทั้งแอป — ตรงกับที่ api/*.py ส่งกลับมา

export type Meeting = {
  day: number;           // 0 = จันทร์ .. 6 = อาทิตย์
  start_min: number;     // นาทีจากเที่ยงคืน เช่น 540 = 09:00
  end_min: number;
  room: string;
  building: string;
  meeting_type: "lecture" | "lab";
};

export type Exam = {
  exam_type: "midterm" | "final";
  exam_date: string;
  start_min: number;
  end_min: number;
  room: string;
};

export type Section = {
  id: string;            // เช่น 04100201-66-01
  section: string;       // เช่น 01
  meetings: Meeting[];
  exams: Exam[];
  seat_total: number | null;
  seat_taken: number | null;
  seat_left: number | null;
  teachers: string[];
  slots_mask: number | null;
};

export type Course = {
  course_code: string;
  course_name: string;
  credits: number;
  category: "major" | "basic" | "general" | "elective" | string;
  suggested_year: number | null;
  prerequisites: string[];
  sections: Section[];
};

export type ConflictCode = "C1" | "C2" | "C3" | "C4" | "C5" | "C6";
export type WarningCode = "W1" | "W2" | "W3" | "W4" | "W5";

export type Suggestion = { action: string; from?: string; to: string; when?: string };

export type Issue = {
  code: ConflictCode | WarningCode | string;
  severity: "ERROR" | "WARNING";
  message_key: string;
  message_th: string;
  subjects: string[];
  detail: Record<string, unknown>;
  suggestions: Suggestion[];
};

export type PlanSummary = {
  total_courses: number;
  total_sections: number;
  total_credits: number;
  min_credits: number;
  max_credits: number;
  credit_status: "ok" | "over" | "under";
  days_on_campus: number;
  free_days: string[];
};

export type ValidateResult = {
  ok: boolean;
  term: string;
  has_conflict: boolean;
  conflicts: Issue[];
  warnings: Issue[];
  summary: PlanSummary;
  unknown_section_ids?: string[];
};

// หมู่เรียนแบบเต็ม (ที่ /api/autoplan ส่งกลับใน plan[])
export type PlannedSection = Section & {
  course_code: string;
  course_name: string;
  credits: number;
  category: string;
  suggested_year?: number | null;
  prerequisites: string[];
};

export type AutoPlanResult = ValidateResult & {
  plan: PlannedSection[];
  skipped: { course_code: string; reason: string }[];
  reached_minimum: boolean;
};

export type Source = {
  doc_id: string;
  title: string;
  section: string;
  doc_type: string;
  score: number;
};

export type ChatResult = {
  ok: boolean;
  answer: string;
  sources: Source[];
  grounded: boolean;
  provider: string;
  disclaimer: string;
};

export type CoursesResult = {
  ok: boolean;
  term: string;
  term_start?: string;   // วันเปิดภาคการศึกษา ใช้คำนวณวันที่จริงตอนส่งออกปฏิทิน
  weeks?: number;        // จำนวนสัปดาห์ที่เรียน
  available_terms: string[];
  credit_rule: { min_credits: number; max_credits: number; summer_max_credits: number };
  disclaimer: string;
  total: number;
  courses: Course[];
};

export const DAY_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"];
export const DAY_SHORT = ["จ", "อ", "พ", "พฤ", "ศ", "ส", "อา"];

export const CATEGORY_LABEL: Record<string, string> = {
  major: "วิชาชีพบังคับ",
  basic: "พื้นฐานวิชาชีพ",
  general: "ศึกษาทั่วไป",
  elective: "วิชาชีพเลือก",
};

/** สีประจำหมวดวิชา ใช้ทั้งในตารางและป้ายกำกับ ให้จำได้ว่าสีไหนคือหมวดไหน */
export const CATEGORY_STYLE: Record<string, { chip: string; block: string; dot: string }> = {
  major: {
    chip: "bg-brand-100 text-brand-800 border-brand-200",
    block: "bg-brand-500/90 border-brand-600 text-white",
    dot: "bg-brand-500",
  },
  basic: {
    chip: "bg-emerald-100 text-emerald-800 border-emerald-200",
    block: "bg-emerald-500/90 border-emerald-600 text-white",
    dot: "bg-emerald-500",
  },
  general: {
    chip: "bg-amber-100 text-amber-900 border-amber-200",
    block: "bg-amber-500/90 border-amber-600 text-white",
    dot: "bg-amber-500",
  },
  elective: {
    chip: "bg-violet-100 text-violet-800 border-violet-200",
    block: "bg-violet-500/90 border-violet-600 text-white",
    dot: "bg-violet-500",
  },
};

export function hhmm(minutes: number): string {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

export function categoryStyle(category: string) {
  return CATEGORY_STYLE[category] ?? CATEGORY_STYLE.general;
}
