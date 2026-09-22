// เก็บแผนของผู้ใช้ไว้ในเบราว์เซอร์
//
// ทำไมไม่ใช้ฐานข้อมูล: Vercel เป็น serverless ไม่มีที่เก็บถาวรให้ และโปรเจกต์นี้
// ไม่มีระบบล็อกอิน การเก็บใน localStorage ทำให้ใช้งานได้ทันทีโดยไม่ต้องสมัครอะไร
// ข้อแลกเปลี่ยน: เปลี่ยนเครื่อง/ล้างข้อมูลเบราว์เซอร์แล้วแผนจะหาย จึงมีปุ่ม
// ส่งออกไฟล์ .ics และคัดลอกรายการไว้ให้

const KEY = "rmutt-planner-v1";

export type SavedState = {
  term: string;
  selectedIds: string[];
  studentYear: number | null;
  passedCourses: string[];
  preferences: { avoidMorning: boolean; freeDays: string[]; maxCredits: number };
};

export const DEFAULT_STATE: SavedState = {
  term: "1/2569",
  selectedIds: [],
  studentYear: null,
  passedCourses: [],
  preferences: { avoidMorning: false, freeDays: [], maxCredits: 21 },
};

export function loadState(): SavedState {
  if (typeof window === "undefined") return DEFAULT_STATE;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULT_STATE;
    return { ...DEFAULT_STATE, ...(JSON.parse(raw) as Partial<SavedState>) };
  } catch {
    // localStorage อาจถูกปิด (โหมดส่วนตัว) — ให้ใช้งานต่อได้ด้วยค่าเริ่มต้น
    return DEFAULT_STATE;
  }
}

export function saveState(state: SavedState): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* เต็มหรือถูกปิด — ไม่ถือเป็นข้อผิดพลาดร้ายแรง */
  }
}

export function clearState(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
