# หน้าเว็บ Next.js ของ 09 — ส่วน /api/* ถูก rewrite ไปที่ container main_api
# (ดู API_PROXY_URL ใน docker-compose.yml และ next.config.mjs)
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
# Next ประเมิน rewrites() ตอน build แล้วฝังผลลงใน routes-manifest.json
# ตั้งค่านี้ตอน runtime อย่างเดียวไม่มีผล /api/* จะ 404 ทั้งหมด (เคยพลาดมาแล้ว)
# ค่าตั้งต้นเป็นชื่อบริการใน docker-compose ซึ่งคงที่อยู่แล้ว
ARG API_PROXY_URL=http://main_api:8009
ENV NEXT_TELEMETRY_DISABLED=1 API_PROXY_URL=$API_PROXY_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 TZ=Asia/Bangkok PORT=3000
RUN apk add --no-cache curl \
    && addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# output: 'standalone' รวม dependency ที่ใช้จริงมาให้แล้ว ไม่ต้องก็อป node_modules ทั้งก้อน
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
# public/ ต้องมีไฟล์อย่างน้อยหนึ่งตัว (มี .gitkeep อยู่) ไม่งั้น git ไม่เก็บโฟลเดอร์
# แล้วตอน build ใน CI จะพังที่บรรทัดนี้ว่า "/app/public": not found
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
