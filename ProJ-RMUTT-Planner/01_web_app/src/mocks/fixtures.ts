import type {
  Course,
  MeResponse,
  Section,
  SourceItem,
  StudentProfile,
  TranscriptCourse,
} from "@/api/types";

/** mock เดียวใช้ตอบทั้ง /auth/login, /auth/me, /students/me/profile — ต้องมี field
 * ครบทั้ง MeResponse (username/student_id/role) และ StudentProfile (program_name/year_level/...) */
export const student: MeResponse & StudentProfile = {
  username: "admin",
  student_id: "6500000000",
  role: "student",
  program_id: "CPE-2566",
  program_name: "วิศวกรรมคอมพิวเตอร์",
  year_level: 3,
  gpax: 3.42,
  credits_earned: 80,
  credits_remaining: 55,
};

export const sources: SourceItem[] = [
  {
    document_id: "demo-regulations",
    title: "ข้อบังคับการศึกษา (ตัวอย่าง)",
    section: "ข้อ 18",
    page: 12,
    url: null,
  },
  {
    document_id: "demo-guide",
    title: "คู่มือคำร้อง (ตัวอย่าง)",
    section: "การยื่นคำร้อง",
    page: 4,
    url: null,
  },
];

export const courses: Course[] = [
  { code: "CPE201", name_th: "โครงสร้างข้อมูล", name_en: "Data Structures", credits: 3 },
  { code: "CPE203", name_th: "ระบบฐานข้อมูล", name_en: "Database Systems", credits: 3 },
  { code: "CPE301", name_th: "วิศวกรรมซอฟต์แวร์", name_en: "Software Engineering", credits: 3 },
  { code: "MAT201", name_th: "คณิตศาสตร์วิศวกรรม", name_en: "Engineering Mathematics", credits: 3 },
  { code: "ENG201", name_th: "ภาษาอังกฤษเพื่อการสื่อสาร", name_en: "English Communication", credits: 3 },
  { code: "CPE204", name_th: "เครือข่ายคอมพิวเตอร์", name_en: "Computer Networks", credits: 3 },
];

const section = (
  courseCode: string,
  courseNameTh: string,
  num: string,
  teacher: string,
  seatsAvailable: number,
  day: Section["meetings"][0]["day"],
  start: string,
  end: string,
  room: string,
): Section => ({
  section_id: `${courseCode}-${num}`,
  course_code: courseCode,
  course_name_th: courseNameTh,
  teacher,
  credits: 3,
  seats_available: seatsAvailable,
  seats_total: 40,
  meetings: [{ day, start, end, room }],
});

export const sections: Section[] = [
  section("CPE201", "โครงสร้างข้อมูล", "01", "อ. ปราณี", 12, "MON", "09:00", "12:00", "ENG 301"),
  section("CPE201", "โครงสร้างข้อมูล", "02", "อ. ปราณี", 8, "TUE", "13:00", "16:00", "ENG 301"),
  section("CPE203", "ระบบฐานข้อมูล", "01", "อ. กิตติ", 6, "MON", "10:00", "12:00", "ENG 402"),
  section("CPE203", "ระบบฐานข้อมูล", "02", "อ. กิตติ", 18, "WED", "09:00", "12:00", "ENG 402"),
  section("CPE301", "วิศวกรรมซอฟต์แวร์", "01", "อ. วิภา", 14, "THU", "13:00", "16:00", "ENG 305"),
  section("CPE301", "วิศวกรรมซอฟต์แวร์", "02", "อ. วิภา", 0, "FRI", "09:00", "12:00", "ENG 305"),
  section("MAT201", "คณิตศาสตร์วิศวกรรม", "01", "อ. ธนา", 9, "TUE", "09:00", "12:00", "SCI 201"),
  section("MAT201", "คณิตศาสตร์วิศวกรรม", "02", "อ. ธนา", 7, "FRI", "13:00", "16:00", "SCI 201"),
  section("ENG201", "ภาษาอังกฤษเพื่อการสื่อสาร", "01", "อ. เมธา", 16, "WED", "13:00", "16:00", "LIB 204"),
  section("ENG201", "ภาษาอังกฤษเพื่อการสื่อสาร", "02", "อ. เมธา", 4, "SAT", "09:00", "12:00", "LIB 204"),
  section("CPE204", "เครือข่ายคอมพิวเตอร์", "01", "อ. ธีร์", 11, "FRI", "09:00", "12:00", "ENG 501"),
  section("CPE204", "เครือข่ายคอมพิวเตอร์", "02", "อ. ธีร์", 5, "THU", "09:00", "12:00", "ENG 501"),
];

export const transcript: TranscriptCourse[] = [
  { course_code: "CPE101", course_name_th: "การเขียนโปรแกรมคอมพิวเตอร์", credits: 3, grade: "A", term: "1/2568" },
  { course_code: "MAT101", course_name_th: "แคลคูลัส 1", credits: 3, grade: "B+", term: "1/2568" },
  { course_code: "PHY101", course_name_th: "ฟิสิกส์ทั่วไป", credits: 3, grade: "F", term: "1/2568" },
  { course_code: "CPE102", course_name_th: "การเขียนโปรแกรมเชิงวัตถุ", credits: 3, grade: "A", term: "2/2568" },
  { course_code: "ENG101", course_name_th: "ภาษาอังกฤษพื้นฐาน", credits: 3, grade: "B+", term: "2/2568" },
];

export const leaveAnswer =
  "เริ่มจากตรวจสอบเงื่อนไขในระเบียบของมหาวิทยาลัย และติดต่อหน่วยงานทะเบียนครับ\n\n1. ตรวจสอบสิทธิ์และช่วงเวลายื่นคำร้อง\n2. เตรียมแบบคำร้องและเอกสารประกอบตามที่กำหนด\n3. ส่งคำร้องผ่านช่องทางของมหาวิทยาลัย\n\nรายละเอียดอาจต่างกันตามคณะ ควรยืนยันกับหน่วยงานทะเบียนก่อนยื่นคำร้อง";
