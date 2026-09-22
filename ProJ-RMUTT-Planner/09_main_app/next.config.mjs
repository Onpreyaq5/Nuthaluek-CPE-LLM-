/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // standalone ทำให้ image เล็กลงมาก เพราะ Next รวม dependency ที่ใช้จริงมาให้
  // ไม่ต้องก็อป node_modules ทั้งก้อนเข้า container
  output: 'standalone',
  // ส่ง /api/* ต่อไปยังฟังก์ชัน Python ที่รันแยก (dev_server.py หรือ container api)
  //
  // ต้องทำงานทั้งโหมด dev และ production เพราะใน Docker เรารันด้วย `next start`
  // ซึ่งเป็น production ถ้าเช็คเฉพาะ development ไว้ /api/* จะ 404 ทั้งหมด
  // บน Vercel ไม่ตั้งตัวแปรนี้ เพราะ api/*.py เป็น serverless function อยู่แล้ว
  async rewrites() {
    // ตัดช่องว่างและ / ท้ายออกก่อน — ถ้าตั้งค่าเผลอติดช่องว่างมา (เช่น `set X=... && cmd` บน Windows)
    // Next จะโยน ERR_INVALID_URL แล้ว /api/* ทั้งหมดกลายเป็น 500 โดยไม่บอกสาเหตุ
    const apiUrl = (process.env.API_PROXY_URL ?? process.env.PY_DEV_URL ?? '')
      .trim().replace(/\/+$/, '');
    if (!apiUrl) return [];
    return [{ source: '/api/:path*', destination: `${apiUrl}/api/:path*` }];
  },
};
export default nextConfig;
