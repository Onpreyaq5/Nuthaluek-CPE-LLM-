#!/bin/sh
# รัน lint + test ของ 02_api_backend แบบครบในคำสั่งเดียว (ใช้แทน CI ระหว่างรอทีมรับข้อเสนอใน
# handoff/ci.md) ต้องมี Docker ให้ใช้งาน — สร้าง Postgres ชั่วคราวเอง ไม่ยุ่งกับ container อื่นที่รันอยู่แล้ว
#
# หมายเหตุ: สภาพแวดล้อมนี้ไม่มี docker-compose.yml ที่ root ให้ใช้ (โมดูลเดี่ยว ไม่ใช่ monorepo เต็ม)
# จึงสร้าง Postgres ด้วย `docker run` ตรงแทน — ถ้ามี compose.yml จริงแล้ว ให้เปลี่ยนมาใช้
# `docker compose up -d postgres` ตามที่ CLAUDE.md ระบุไว้แทนส่วนนี้
#
# ใช้: sh scripts/test.sh   (รันจากโฟลเดอร์ 02_api_backend/)

set -e

CONTAINER_NAME="rmutt-api-test-pg"
DB_USER="rmutt"
DB_PASSWORD="change_me_please"
DB_NAME="rmutt_test"

cleanup() {
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
# ปล่อยให้ Docker เลือกพอร์ตของโฮสต์เอง กันชนกับ Postgres อื่นที่อาจรันอยู่แล้วบนเครื่อง (เช่นพอร์ต 5432 เดิม)
docker run -d --name "$CONTAINER_NAME" \
  -e POSTGRES_USER="$DB_USER" \
  -e POSTGRES_PASSWORD="$DB_PASSWORD" \
  -e POSTGRES_DB="$DB_NAME" \
  -p 127.0.0.1::5432 \
  postgres:16-alpine >/dev/null

DB_PORT=$(docker port "$CONTAINER_NAME" 5432/tcp | head -n1 | cut -d: -f2)
if [ -z "$DB_PORT" ]; then
  echo "หาพอร์ตของ Postgres container ไม่เจอ" >&2
  exit 1
fi

echo "รอ Postgres พร้อมใช้งาน..."
ready=0
for _ in $(seq 1 30); do
  if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [ "$ready" -ne 1 ]; then
  echo "Postgres ไม่พร้อมภายในเวลาที่กำหนด" >&2
  exit 1
fi

export TEST_DATABASE_URL="postgresql+psycopg://$DB_USER:$DB_PASSWORD@localhost:$DB_PORT/$DB_NAME"

echo "=== ruff check . ==="
ruff check .

echo "=== pytest -q ==="
pytest -q
