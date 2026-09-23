import { Fragment, type ReactNode } from "react";

/** แสดงข้อความจาก AI ที่เขียนแบบ Markdown พื้นฐาน: ย่อหน้า, ขึ้นบรรทัด, รายการ "- ", ตัวหนา **...**
 *
 * คำตอบของ 07 และ Gemini ใช้ Markdown ถ้าแสดงเป็น string ตรง ๆ ผู้ใช้จะเห็น "**" ดิบ
 * และบรรทัดใหม่หายหมด (คำอธิบายแผนทั้งก้อนกลายเป็นย่อหน้าเดียว)
 *
 * สร้างเป็น React element ทั้งหมด ไม่ใช้ dangerouslySetInnerHTML — ข้อความถูก escape เสมอ
 * คำตอบที่มี <script> หรือ HTML แปลก ๆ จะแสดงเป็นตัวอักษร ไม่ถูกรัน */
function inline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const parts = text.split("**");
  parts.forEach((part, i) => {
    if (!part) return;
    // ส่วนเลขคี่อยู่ระหว่าง ** คู่หนึ่ง; ถ้า ** ไม่ครบคู่ ส่วนสุดท้ายแสดงเป็นข้อความธรรมดา
    const bold = i % 2 === 1 && i < parts.length - 1;
    out.push(
      bold ? (
        <strong key={`${keyBase}-${i}`}>{part}</strong>
      ) : (
        <Fragment key={`${keyBase}-${i}`}>{part}</Fragment>
      ),
    );
  });
  return out;
}

const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/;

export function RichText({ text, className }: { text: string; className?: string }) {
  const blocks = text.replace(/\r\n/g, "\n").split(/\n{2,}/);
  return (
    <div className={["rich-text", className].filter(Boolean).join(" ")}>
      {blocks.map((block, b) => {
        const lines = block.split("\n").filter((l) => l.trim() !== "");
        if (!lines.length) return null;
        const bulletLines = lines.filter((l) => BULLET.test(l));
        // ทั้งก้อนเป็นรายการ -> <ul>; ถ้าปนกัน แสดงบรรทัดหัวเป็นย่อหน้าแล้วตามด้วยรายการ
        if (bulletLines.length === lines.length) {
          return (
            <ul key={b}>
              {lines.map((l, i) => (
                <li key={i}>{inline(l.replace(BULLET, ""), `${b}-${i}`)}</li>
              ))}
            </ul>
          );
        }
        const firstBullet = lines.findIndex((l) => BULLET.test(l));
        if (firstBullet > 0 && lines.slice(firstBullet).every((l) => BULLET.test(l))) {
          return (
            <Fragment key={b}>
              <p>
                {lines.slice(0, firstBullet).map((l, i) => (
                  <Fragment key={i}>
                    {i > 0 && <br />}
                    {inline(l, `${b}-h${i}`)}
                  </Fragment>
                ))}
              </p>
              <ul>
                {lines.slice(firstBullet).map((l, i) => (
                  <li key={i}>{inline(l.replace(BULLET, ""), `${b}-l${i}`)}</li>
                ))}
              </ul>
            </Fragment>
          );
        }
        return (
          <p key={b}>
            {lines.map((l, i) => (
              <Fragment key={i}>
                {i > 0 && <br />}
                {inline(l, `${b}-${i}`)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
