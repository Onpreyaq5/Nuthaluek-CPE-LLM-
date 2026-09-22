import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CalendarRange,
  CheckCircle2,
  Clock,
  Coins,
  CopyX,
  FileWarning,
  Lock,
  MessageCircleQuestion,
  MousePointerClick,
  Sparkles,
  Users,
  Zap,
} from "lucide-react";

/** 3 ขั้นตอน — ลดความกลัวว่า "จะต้องทำอะไรยาก ๆ" ก่อนกดเริ่ม */
const STEPS = [
  {
    icon: MousePointerClick,
    title: "บอกว่าคุณอยู่ปีไหน",
    desc: "เลือกชั้นปีกับภาคการศึกษา ไม่ต้องกรอกอะไรอีก",
  },
  {
    icon: Zap,
    title: "กดปุ่มเดียว",
    desc: "ระบบเลือกวิชาที่ควรลง จัดเวลาไม่ให้ชน คุมหน่วยกิตให้อยู่ 9–21",
  },
  {
    icon: CalendarRange,
    title: "ได้ตารางพร้อมใช้",
    desc: "ปรับเองต่อได้ แล้วเซฟเข้า Google Calendar",
  },
];

/** 6 อย่างที่ตรวจให้ — ตรงกับรหัส C1–C6 ของเครื่องตรวจตารางชน */
const CHECKS = [
  { icon: Clock, label: "เวลาเรียนชนกัน", note: "เทียบทุกคาบ ทุกวัน" },
  { icon: FileWarning, label: "เวลาสอบชนกัน", note: "ทั้งกลางภาคและปลายภาค" },
  { icon: Lock, label: "วิชาบังคับก่อน", note: "ยังไม่ผ่านตัวไหน ลงตัวต่อไม่ได้" },
  { icon: Coins, label: "หน่วยกิตเกิน/ขาด", note: "ตามระเบียบ 9–21 ต่อเทอม" },
  { icon: CopyX, label: "ลงวิชาซ้ำ", note: "ซ้ำหมู่ หรือเคยผ่านแล้ว" },
  { icon: Users, label: "ที่นั่งเต็ม", note: "บอกก่อนถึงวันลงทะเบียน" },
];

const FEATURES = [
  {
    href: "/planner",
    icon: CalendarRange,
    title: "จัดตารางเรียน",
    desc: "เลือกวิชาแล้วเห็นตารางทันที ชนตรงไหนขึ้นสีแดงให้เห็นเลย พร้อมปุ่มสลับหมู่แก้ให้ในคลิกเดียว",
    cta: "เริ่มจัดตาราง",
    primary: true,
  },
  {
    href: "/courses",
    icon: BookOpen,
    title: "ค้นหารายวิชา",
    desc: "รายวิชาที่เปิดสอน หมู่เรียน วัน–เวลา อาจารย์ และที่นั่งคงเหลือ ครบในหน้าเดียว",
    cta: "ดูรายวิชา",
    primary: false,
  },
  {
    href: "/chat",
    icon: MessageCircleQuestion,
    title: "ถามเรื่องระเบียบ",
    desc: "ถอนวิชาได้ถึงเมื่อไหร่ ลงได้กี่หน่วยกิต ตอบพร้อมบอกว่าอ้างจากเอกสารไหน ข้อไหน",
    cta: "ถามคำถาม",
    primary: false,
  },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      {/* ── HOOK: พูดถึงความเจ็บปวดก่อน แล้วค่อยเสนอทางออก ── */}
      <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 px-6 py-12 text-white sm:px-10 sm:py-14">
        <p className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          วิศวกรรมคอมพิวเตอร์ · มทร.ธัญบุรี
        </p>

        <h1 className="mt-4 max-w-3xl text-3xl font-bold leading-snug sm:text-[2.6rem] sm:leading-tight">
          ลงทะเบียนทีไร ลุ้นทุกที
          <br className="hidden sm:block" />
          <span className="text-gold-400"> ว่าตารางจะชนหรือเปล่า</span>
        </h1>

        <p className="mt-4 max-w-xl text-base leading-relaxed text-brand-50">
          เลือกวิชาที่อยากลง แล้วให้ระบบตรวจให้ทันที — เวลาเรียนชน เวลาสอบชน
          วิชาบังคับก่อนยังไม่ผ่าน หน่วยกิตเกิน ที่นั่งเต็ม
          <strong className="text-white"> รู้ก่อนวันลงทะเบียนจริง</strong>
        </p>

        <div className="mt-7 flex flex-wrap items-center gap-3">
          <Link
            href="/planner"
            className="btn bg-white px-6 py-3 text-base font-semibold text-brand-700 shadow-lg hover:bg-brand-50"
          >
            <CalendarRange className="h-5 w-5" aria-hidden />
            จัดตารางให้ฉันเลย
            <ArrowRight className="h-5 w-5" aria-hidden />
          </Link>
          <Link href="/chat" className="btn border border-white/30 px-5 py-3 text-white hover:bg-white/10">
            <MessageCircleQuestion className="h-4 w-4" aria-hidden />
            ถามเรื่องระเบียบ
          </Link>
        </div>

        {/* ลดแรงต้านก่อนกด — ทั้งสามข้อนี้เป็นความจริงของระบบ */}
        <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-sm text-brand-100">
          {["ไม่ต้องสมัครสมาชิก", "ไม่ต้องกรอกรหัสนักศึกษา", "ใช้ฟรี"].map((t) => (
            <li key={t} className="flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-gold-400" aria-hidden />
              {t}
            </li>
          ))}
        </ul>
      </section>

      {/* ── ใช้ยังไง: 3 ขั้นจบ ── */}
      <section>
        <h2 className="text-xl font-semibold text-slate-900">ใช้ยังไง</h2>
        <p className="mt-1 text-sm text-slate-600">สามขั้นตอน ใช้เวลาไม่ถึงนาที</p>
        <ol className="mt-4 grid gap-4 sm:grid-cols-3">
          {STEPS.map(({ icon: Icon, title, desc }, i) => (
            <li key={title} className="card relative p-5">
              <span className="absolute right-4 top-4 text-3xl font-bold text-slate-100" aria-hidden>
                {i + 1}
              </span>
              <span className="grid h-10 w-10 place-items-center rounded-lg bg-brand-50 text-brand-600">
                <Icon className="h-5 w-5" aria-hidden />
              </span>
              <h3 className="mt-3 font-semibold text-slate-900">{title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-600">{desc}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ── ตรวจอะไรให้: พิสูจน์ว่าไม่ใช่แค่ปฏิทินสวย ๆ ── */}
      <section className="card p-6">
        <h2 className="text-xl font-semibold text-slate-900">ระบบตรวจให้ 6 อย่าง</h2>
        <p className="mt-1 text-sm text-slate-600">
          ตรวจด้วยการคำนวณตรง ๆ ไม่ได้ใช้ AI เดา
          <strong className="text-slate-800"> ผลจึงเหมือนเดิมทุกครั้งและเชื่อถือได้</strong>
        </p>
        <ul className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {CHECKS.map(({ icon: Icon, label, note }) => (
            <li key={label} className="flex gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-600">
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium text-slate-800">{label}</span>
                <span className="block text-xs text-slate-500">{note}</span>
              </span>
            </li>
          ))}
        </ul>
      </section>

      {/* ── เมนูหลัก ── */}
      <section>
        <h2 className="text-xl font-semibold text-slate-900">ใช้งานอะไรได้บ้าง</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {FEATURES.map(({ href, icon: Icon, title, desc, cta, primary }) => (
            <Link
              key={href}
              href={href}
              className={[
                "card group flex flex-col p-5 transition hover:-translate-y-0.5 hover:shadow-md",
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

      {/* ── CTA ปิดท้าย ── */}
      <section className="card flex flex-col items-center gap-4 bg-slate-900 p-8 text-center text-white sm:flex-row sm:justify-between sm:text-left">
        <div>
          <h2 className="text-lg font-semibold">พร้อมจัดตารางเทอมหน้าแล้วหรือยัง</h2>
          <p className="mt-1 text-sm text-slate-300">
            ลองดูก่อนได้ ไม่ต้องสมัคร ไม่ต้องกรอกอะไร แผนที่จัดไว้จะถูกจำไว้ในเครื่องคุณเอง
          </p>
        </div>
        <Link
          href="/planner"
          className="btn shrink-0 bg-white px-6 py-3 font-semibold text-slate-900 hover:bg-slate-100"
        >
          เริ่มเลย
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </section>

      {/* ── ความโปร่งใสเรื่องข้อมูล: บอกตรง ๆ ดีกว่าให้ผู้ใช้มารู้ทีหลัง ── */}
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
