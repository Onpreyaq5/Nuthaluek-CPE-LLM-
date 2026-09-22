/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // ระหว่าง dev ในเครื่อง ให้ /api/* วิ่งไปที่ Python ที่รันแยก (dev_server.py)
  // บน Vercel ไม่ใช้ rewrite เพราะ api/*.py เป็น serverless function อยู่แล้ว
  async rewrites() {
    // ตัดช่องว่างและ / ท้ายออกก่อน — ถ้าตั้งค่าเผลอติดช่องว่างมา (เช่น `set X=... && cmd` บน Windows)
    // Next จะโยน ERR_INVALID_URL แล้ว /api/* ทั้งหมดกลายเป็น 500 โดยไม่บอกสาเหตุ
    const pyUrl = (process.env.PY_DEV_URL ?? '').trim().replace(/\/+$/, '');
    if (process.env.NODE_ENV === 'development' && pyUrl) {
      return [{ source: '/api/:path*', destination: `${pyUrl}/api/:path*` }];
    }
    return [];
  },
};
export default nextConfig;
