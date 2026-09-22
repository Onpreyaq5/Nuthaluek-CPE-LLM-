"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, CalendarRange, GraduationCap, MessageCircleQuestion } from "lucide-react";

// short = ป้ายบนจอมือถือ ต้องสั้นพอให้สี่เมนูเรียงในบรรทัดเดียวที่ 375px
const LINKS = [
  { href: "/", label: "หน้าแรก", short: "หน้าแรก", icon: GraduationCap },
  { href: "/planner", label: "จัดตารางเรียน", short: "จัดตาราง", icon: CalendarRange },
  { href: "/courses", label: "ค้นหารายวิชา", short: "รายวิชา", icon: BookOpen },
  { href: "/chat", label: "ถามเรื่องระเบียบ", short: "ถาม-ตอบ", icon: MessageCircleQuestion },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-2 px-4 py-3 sm:px-6">
        <Link href="/" className="mr-2 flex shrink-0 items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-600 text-white">
            <GraduationCap className="h-5 w-5" aria-hidden />
          </span>
          <span className="hidden leading-tight sm:block">
            <span className="block text-sm font-semibold text-slate-900">วางแผนการเรียน</span>
            <span className="block text-[11px] text-slate-500">มทร.ธัญบุรี · วิศวกรรมคอมพิวเตอร์</span>
          </span>
        </Link>

        <nav aria-label="เมนูหลัก" className="ml-auto flex items-center gap-0.5 sm:gap-1">
          {LINKS.map(({ href, label, short, icon: Icon }) => {
            const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                aria-label={label}
                className={[
                  // มือถือเรียงไอคอนทับป้ายสั้น เดสก์ท็อปเรียงแนวนอนพร้อมป้ายเต็ม
                  // ถ้าเหลือแต่ไอคอนเปล่า ผู้ใช้ใหม่เดาไม่ออกว่าปุ่มไหนคืออะไร
                  "flex shrink-0 flex-col items-center gap-0.5 rounded-lg px-2 py-1.5 text-sm font-medium transition",
                  "sm:flex-row sm:gap-1.5 sm:px-3 sm:py-2",
                  active
                    ? "bg-brand-50 text-brand-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                ].join(" ")}
              >
                <Icon className="h-5 w-5 sm:h-4 sm:w-4" aria-hidden />
                <span className="text-[10px] leading-none sm:hidden">{short}</span>
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
