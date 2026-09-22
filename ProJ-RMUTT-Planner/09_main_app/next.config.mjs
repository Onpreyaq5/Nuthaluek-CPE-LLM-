/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // ระหว่าง dev ในเครื่อง ให้ /api/* วิ่งไปที่ Python ที่รันแยก (dev_server.py)
  // บน Vercel ไม่ใช้ rewrite เพราะ api/*.py เป็น serverless function อยู่แล้ว
  async rewrites() {
    if (process.env.NODE_ENV === 'development' && process.env.PY_DEV_URL) {
      return [{ source: '/api/:path*', destination: `${process.env.PY_DEV_URL}/api/:path*` }];
    }
    return [];
  },
};
export default nextConfig;
