#!/bin/sh
# จำลอง "clean clone" smoke test: build image จริง, รันเป็น container จริงคู่กับ Postgres+Redis
# แล้วยิง curl ตามลำดับ flow ที่ 01 จะใช้จริง: login -> courses -> validate -> save -> chat
#
# หมายเหตุ: สภาพแวดล้อมนี้ไม่มี docker-compose.yml ที่ root (โมดูลเดี่ยว ไม่ใช่ monorepo เต็ม)
# จึงต่อ container กันเองผ่าน `docker network` แทน `docker compose` — ดู handoff/compose.md
# สำหรับข้อเสนอ compose.yml จริงที่ทีมเอาไปรวมได้
#
# adapter 04-08 ใช้ mock ทั้งหมด (self-contained ไม่ต้องพึ่งโมดูลอื่นที่ยังไม่มี) ยกเว้น 03 (ROUTER_URL)
# ซึ่งใช้ http เสมอตาม CLAUDE.md ข้อ 7 — ยังไม่มี router จริงให้ต่อ (ดู PROGRESS.md) จึง "ทดสอบว่า
# 02 จัดการ upstream ที่ล่มอย่างถูกต้อง" แทนการเรียกแชตสำเร็จจริง (คาดหวัง UPSTREAM_502 ที่มี envelope ถูกต้อง)
#
# ใช้: sh scripts/smoke.sh   (รันจากโฟลเดอร์ 02_api_backend/)

set -e

NETWORK="rmutt-smoke-net"
PG_CONTAINER="rmutt-smoke-pg"
REDIS_CONTAINER="rmutt-smoke-redis"
API_CONTAINER="rmutt-smoke-api"
IMAGE_TAG="rmutt-api-smoke"
DB_USER="rmutt"
DB_PASSWORD="change_me_please"
DB_NAME="rmutt_smoke"
COOKIE_JAR=$(mktemp)

cleanup() {
  echo "=== ล้าง container/network ชั่วคราว ==="
  docker rm -f "$API_CONTAINER" "$PG_CONTAINER" "$REDIS_CONTAINER" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -f "$COOKIE_JAR"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $1" >&2
  echo "--- logs จาก $API_CONTAINER ---" >&2
  docker logs "$API_CONTAINER" >&2 2>&1 || true
  exit 1
}

cleanup >/dev/null 2>&1 || true
docker network create "$NETWORK" >/dev/null

echo "=== build image ==="
docker build -t "$IMAGE_TAG" . >/dev/null

echo "=== เริ่ม Postgres + Redis ==="
docker run -d --name "$PG_CONTAINER" --network "$NETWORK" \
  -e POSTGRES_USER="$DB_USER" -e POSTGRES_PASSWORD="$DB_PASSWORD" -e POSTGRES_DB="$DB_NAME" \
  postgres:16-alpine >/dev/null
docker run -d --name "$REDIS_CONTAINER" --network "$NETWORK" redis:7-alpine >/dev/null

echo "รอ Postgres พร้อมใช้งาน..."
ready=0
for _ in $(seq 1 30); do
  if docker exec "$PG_CONTAINER" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || fail "Postgres ไม่พร้อมภายในเวลาที่กำหนด"

echo "=== เริ่ม api container (migrate -> seed -> uvicorn ผ่าน entrypoint.sh) ==="
docker run -d --name "$API_CONTAINER" --network "$NETWORK" -p 127.0.0.1::8000 \
  -e DATABASE_URL="postgresql+psycopg://$DB_USER:$DB_PASSWORD@$PG_CONTAINER:5432/$DB_NAME" \
  -e REDIS_URL="redis://$REDIS_CONTAINER:6379/0" \
  -e SEED_DEMO=true \
  -e DEMO_USERNAME=admin -e DEMO_PASSWORD=admin1234 -e DEMO_STUDENT_ID=6500000000 \
  -e JWT_SECRET=smoke-test-secret \
  -e CORS_ORIGINS=http://localhost:5173 \
  -e ADAPTER_04=mock -e ADAPTER_05=mock -e ADAPTER_06=mock -e ADAPTER_07=mock -e ADAPTER_08=mock \
  -e ROUTER_URL=http://router-not-available:8001 \
  -e TIMEOUT_CHAT_START_SECONDS=3 \
  "$IMAGE_TAG" >/dev/null

API_PORT=$(docker port "$API_CONTAINER" 8000/tcp | head -n1 | cut -d: -f2)
[ -n "$API_PORT" ] || fail "หาพอร์ตของ api container ไม่เจอ"
BASE_URL="http://localhost:$API_PORT"

echo "รอ api พร้อมใช้งาน (รอ /health)..."
ready=0
for _ in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" 2>/dev/null | grep -q "^200$"; then
    ready=1
    break
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || fail "api ไม่พร้อมภายในเวลาที่กำหนด (/health ไม่ตอบ 200)"

echo "=== 1) login ==="
LOGIN_STATUS=$(curl -s -o /tmp/smoke_login.json -w "%{http_code}" -c "$COOKIE_JAR" \
  -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin1234"}')
[ "$LOGIN_STATUS" = "200" ] || fail "login คืนสถานะ $LOGIN_STATUS (คาดหวัง 200): $(cat /tmp/smoke_login.json)"
grep -q '"ok":true' /tmp/smoke_login.json || fail "login envelope ไม่มี ok:true"
echo "OK login"

echo "=== 2) courses ==="
COURSES_STATUS=$(curl -s -o /tmp/smoke_courses.json -w "%{http_code}" -b "$COOKIE_JAR" \
  "$BASE_URL/api/v1/courses")
[ "$COURSES_STATUS" = "200" ] || fail "courses คืนสถานะ $COURSES_STATUS (คาดหวัง 200): $(cat /tmp/smoke_courses.json)"
grep -q '"ok":true' /tmp/smoke_courses.json || fail "courses envelope ไม่มี ok:true"
echo "OK courses"

echo "=== 3) validate plan ==="
VALIDATE_STATUS=$(curl -s -o /tmp/smoke_validate.json -w "%{http_code}" -b "$COOKIE_JAR" \
  -X POST "$BASE_URL/api/v1/plans/validate" \
  -H "Content-Type: application/json" \
  -d '{"term":"1/2569","section_ids":["CPE201-01"]}')
[ "$VALIDATE_STATUS" = "200" ] || fail "validate คืนสถานะ $VALIDATE_STATUS (คาดหวัง 200): $(cat /tmp/smoke_validate.json)"
grep -q '"ok":true' /tmp/smoke_validate.json || fail "validate envelope ไม่มี ok:true"
echo "OK validate"

echo "=== 4) save plan ==="
SAVE_STATUS=$(curl -s -o /tmp/smoke_save.json -w "%{http_code}" -b "$COOKIE_JAR" \
  -X POST "$BASE_URL/api/v1/plans" \
  -H "Content-Type: application/json" \
  -d '{"term":"1/2569","name":"smoke test plan","section_ids":["CPE201-01"]}')
[ "$SAVE_STATUS" = "200" ] || fail "save plan คืนสถานะ $SAVE_STATUS (คาดหวัง 200): $(cat /tmp/smoke_save.json)"
grep -q '"ok":true' /tmp/smoke_save.json || fail "save plan envelope ไม่มี ok:true"
echo "OK save plan"

echo "=== 5) chat (คาดหวัง UPSTREAM_502 เพราะยังไม่มี router (03) จริงให้ต่อ ใน smoke นี้) ==="
CHAT_STATUS=$(curl -s -o /tmp/smoke_chat.json -w "%{http_code}" -b "$COOKIE_JAR" \
  -X POST "$BASE_URL/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id":null,"message":"ทดสอบ smoke"}')
if [ "$CHAT_STATUS" = "502" ] && grep -q '"UPSTREAM_502"' /tmp/smoke_chat.json; then
  echo "OK chat (จัดการ upstream ล่มถูกต้อง — ยังไม่มี router (03) จริงให้ต่อในสภาพแวดล้อมนี้)"
elif [ "$CHAT_STATUS" = "200" ]; then
  echo "OK chat (มี router (03) จริงตอบสนอง)"
else
  fail "chat คืนสถานะ $CHAT_STATUS ที่ไม่คาดคิด: $(cat /tmp/smoke_chat.json)"
fi

echo ""
echo "=== smoke test ผ่านทั้งหมด ==="
