import type { Metadata, Viewport } from "next";
import "./globals.css";
import { NavBar } from "./components/NavBar";

export const metadata: Metadata = {
  title: "วางแผนการเรียน มทร.ธัญบุรี | RMUTT Study Planner",
  description:
    "จัดตารางเรียน ตรวจตารางชน และถามเรื่องระเบียบการลงทะเบียน สำหรับนักศึกษาวิศวกรรมคอมพิวเตอร์ มทร.ธัญบุรี",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#1f45d8",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+Thai:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <NavBar />
        <main className="mx-auto w-full max-w-7xl px-4 pb-16 pt-6 sm:px-6">{children}</main>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-7xl px-4 py-6 text-center text-xs text-slate-500 sm:px-6">
            <p className="font-medium text-slate-600">
              ระบบวางแผนการเรียน มหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี
            </p>
            <p className="mt-1">
              ข้อมูลในระบบเป็น<strong className="text-amber-700">ข้อมูลจำลองสำหรับต้นแบบ</strong>{" "}
              ไม่ใช่ตารางสอนจริง · โปรดยืนยันกับระบบทะเบียนก่อนลงทะเบียนจริงทุกครั้ง
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
