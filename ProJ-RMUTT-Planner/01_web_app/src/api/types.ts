import type { components } from "./schema";

export type Course = components["schemas"]["Course"];
export type Section = components["schemas"]["Section"];
export type Meeting = components["schemas"]["MeetingSlot"];
export type SourceItem = components["schemas"]["SourceItem"];
export type ChatMessage = components["schemas"]["ChatMessage"];
export type ChatSessionSummary = components["schemas"]["ChatSessionSummary"];
export type PlanSummary = components["schemas"]["PlanSummary"];
export type PlanCreateResponse = components["schemas"]["PlanCreateResponse"];
export type PlanDetail = components["schemas"]["PlanDetail"];
export type ConflictItem = components["schemas"]["ConflictItem"];
export type WarningItem = components["schemas"]["WarningItem"];
export type ValidateSummary = components["schemas"]["ValidateSummary"];
export type Validation = components["schemas"]["PlanValidateResponse"];
export type GeneratedPlan = components["schemas"]["GeneratedPlan"];
export type AutoPlanResponse = components["schemas"]["AutoPlanResponse"];
export type TranscriptCourse = components["schemas"]["TranscriptCourse"];
export type TranscriptResponse = components["schemas"]["TranscriptResponse"];
export type ImportResult = components["schemas"]["ImportResult"];
export type ChatRequest = components["schemas"]["ChatRequest"];
export type StudentProfile = components["schemas"]["StudentProfile"];
export type StudentPreferences = components["schemas"]["StudentPreferences"];
export type MeResponse = components["schemas"]["MeResponse"];
export type LoginResponse = components["schemas"]["LoginResponse"];
export type ExplainResponse = components["schemas"]["ExplainResponse"];
export type Day = Meeting["day"];

/** 02 ไม่มี field ชื่อคนเลย (username/student_id เท่านั้น) — โครงนี้คือสิ่งที่แอปมีให้ใช้จริง
 * ประกอบจาก MeResponse + StudentProfile ตอน login/refresh (ดู App.tsx) */
export type CurrentUser = MeResponse & Partial<StudentProfile>;
