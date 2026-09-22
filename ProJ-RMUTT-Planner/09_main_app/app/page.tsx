import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CalendarRange,
  CheckCircle2,
  MessageCircleQuestion,
  Sparkles,
} from "lucide-react";

const FEATURES = [
  {
    href: "/planner",
    icon: CalendarRange,
    title: "จัดตารางเรียน",
    desc: "เลือกวิชาแล้วเห็นตารางทันที ระบบเช็คให้ว่าเวลาเรียนหรือเวลาสอบชนกันไหม",
    cta: "เริ่มจัดตาราง",
    primary: true,
  },
  {
    href: "/courses",
    icon: BookOpen,
    title: "ค้นหารายวิชา",
    desc: "ดูรายวิชาที่เปิดสอน หมู่เรียน เวลา อาจารย์ และที่นั่งคงเหลือ",
    cta: "ดูรายวิชา",
    primary: false,
  },
  {
    href: "/chat",
    icon: MessageCircleQuestion,
    title: "ถามเรื่องระเบียบ",
    desc: "ถอนวิชาได้ถึงเมื่อไหร่ ลงได้กี่หน่วยกิต ตอบพร้อมอ้างอิงเอกสารจริง",
    cta: "ถามคำถาม",
    primary: false,
  },
];

const CHECKS = [
  "เวลาเรียนชนกัน",
  "เวลาสอบชนกัน",
  "ยังไม่ผ่านวิชาบังคับก่อน",
  "หน่วยกิตเกิน 21 หรือต่ำกว่า 9",
  "ลงวิชาซ้ำ",
  "ที่นั่งเต็ม",
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="rounded-2xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 px-6 py-12 text-white sm:px-10">
        <p className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          สำหรับนักศึกษาวิศวกรรมคอมพิวเตอร์ มทร.ธัญบุรี
        </p>
        <h1 className="mt-4 max-w-2xl text-3xl font-bold leading-tight sm:text-4xl">
          วางแผนการเรียนให้จบตรงเวลา
          <br className="hidden sm:block" />
          โดยไม่ต้องกลัวตารางชน
        </h1>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-brand-100 sm:text-base">
          เลือกวิชาที่อยากลง ระบบตรวจให้ทันทีว่าเวลาเรียนหรือเวลาสอบทับกันไหม
          หน่วยกิตอยู่ในเกณฑ์หรือเปล่า และผ่านวิชาบังคับก่อนครบหรือยัง
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/planner" className="btn bg-white px-5 py-3 text-brand-700 hover:bg-brand-50">
            <CalendarRange className="h-4 w-4" aria-hidden />
            เริ่มจัดตารางเรียน
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Link>
          <Link href="/chat" className="btn border border-white/30 px-5 py-3 text-white hover:bg-white/10">
            <MessageCircleQuestion className="h-4 w-4" aria-hidden />
            ถามเรื่องระเบียบ
          </Link>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-900">ใช้งานอะไรได้บ้าง</h2>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          {FEATURES.map(({ href, icon: Icon, title, desc, cta, primary }) => (
            <Link
              key={href}
              href={href}
              className={[
                "card group flex flex-col p-5 transition hover:shadow-md",
                primary ? "ring-1 ring-brand-200" : "",
              ].join(" ")}
            >
              <span
                className={[
                  "grid h-10 w-10 place-items-center rounded-lg",
                  primary ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-600",
                ].join(" ")}
              >
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="mt-3 font-semibold text-slate-900">{title}</h3>
              <p className="mt-1 flex-1 text-sm leading-relaxed text-slate-600">{desc}</p>
              <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700">
                {cta}
                <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" aria-hidden />
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="card p-6">
        <h2 className="text-lg font-semibold text-slate-900">ระบบตรวจอะไรให้บ้าง</h2>
        <p className="mt-1 text-sm text-slate-600">
          ตรวจด้วยการคำนวณตรง ๆ ไม่ได้ใช้ AI เดา ผลจึงเหมือนเดิมทุกครั้งและถูกต้อง 100%
        </p>
        <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {CHECKS.map((c) => (
            <li key={c} className="flex items-center gap-2 text-sm text-slate-700">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden />
              {c}
            </li>
          ))}
        </ul>
      </section>

      <section className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden />
        <div className="text-sm text-amber-900">
          <p className="font-semibold">ข้อมูลในระบบนี้เป็นข้อมูลจำลองสำหรับต้นแบบ</p>
          <p className="mt-1 leading-relaxed">
            ตารางสอน ระเบียบ และปฏิทินการศึกษาที่ใช้ เป็นชุดข้อมูลตัวอย่างที่สร้างขึ้นเพื่อสาธิตระบบ
            ไม่ใช่ข้อมูลจริงจากมหาวิทยาลัย{" "}
            <strong>โปรดตรวจสอบกับระบบทะเบียนและอาจารย์ที่ปรึกษาก่อนลงทะเบียนจริงทุกครั้ง</strong>
          </p>
        </div>
      </section>
    </div>
  );
}
