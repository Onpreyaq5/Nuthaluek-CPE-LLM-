// คัดลอกข้อมูลจากโมดูล 07 (แหล่งข้อมูลหลัก) มาไว้ใน 09
//
// ทำไมต้องคัดลอก: Vercel bundle เฉพาะไฟล์ที่อยู่ใต้โฟลเดอร์โปรเจกต์
// อ้างข้ามไปโฟลเดอร์พี่น้องไม่ได้ จึงต้องมีสำเนา
// แก้ข้อมูลที่ 07 แล้วรัน `npm run sync-data` เพื่ออัปเดตสำเนานี้
import { cp, mkdir, readdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const app = join(here, "..");
const source = join(app, "..", "07_rag_llm_engine", "data");

for (const folder of ["knowledge", "seed"]) {
  const from = join(source, folder);
  const to = join(app, "data", folder);
  await mkdir(to, { recursive: true });
  const files = (await readdir(from)).filter((f) => f.endsWith(".md") || f.endsWith(".json"));
  for (const f of files) await cp(join(from, f), join(to, f));
  console.log(`  ${folder}: ${files.length} ไฟล์`);
}
console.log("คัดลอกข้อมูลจากโมดูล 07 เรียบร้อย");
