import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
/** section_id จริงจาก 02 คือ "CPE301-01" ทั้งก้อน (ไม่มี field เลขหมู่แยก) — ใช้ส่วนท้ายเป็นเลขหมู่แสดงผล */
export function sectionNumber(sectionId: string) {
  return sectionId.split("-").pop() ?? sectionId;
}
