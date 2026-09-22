#!/usr/bin/env bash
# ยกระบบทั้งหมดขึ้นด้วย Docker แล้วตรวจให้ครบ จบในคำสั่งเดียว
#
#   cd ProJ-RMUTT-Planner
#   bash scripts/verify_docker.sh
#
# ตรวจตามลำดับ
#   1. build ทุกบริการ
#   2. ยกขึ้นแล้วรอจนพร้อม
#   3. ทุก container ต้องอยู่สถานะ running ไม่มีตัวไหนตายหรือวนรีสตาร์ต
#   4. ยิง endpoint จริงของแต่ละบริการ
#   5. ตรวจว่าเรียกข้ามบริการได้จริง (ไม่ใช่แค่ตัวเองขึ้น)
#
# ออกด้วยรหัส 0 เมื่อผ่านหมด ไม่ผ่านจะพิมพ์ log ของตัวที่มีปัญหาให้เลย
set -uo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  \033[32mผ่าน\033[0m  %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  \033[31mตก\033[0m    %s\n' "$1"; }
head() { printf '\n\033[1m%s\033[0m\n' "$1"; }

[ -f .env ] || { echo "ยังไม่มี .env — คัดลอกจากตัวอย่างให้แล้ว"; cp .env.example .env; }

head "1. build ทุกบริการ"
if docker compose build; then ok "build ผ่านทุกบริการ"; else
  bad "build ไม่ผ่าน"; echo; echo "หยุดตรงนี้ เพราะไม่มีอะไรให้รันต่อ"; exit 1
fi

head "2. ยกระบบขึ้น"
docker compose up -d || { bad "docker compose up ไม่สำเร็จ"; docker compose logs --tail 80; exit 1; }
ok "สั่งขึ้นแล้ว"

head "3. รอให้พร้อม (สูงสุด 180 วินาที)"
for i in $(seq 1 60); do
  if curl -fsS --max-time 3 http://localhost:3000/ >/dev/null 2>&1 \
  && curl -fsS --max-time 3 http://localhost:8700/health >/dev/null 2>&1; then
    ok "บริการหลักตอบแล้ว (ใช้เวลา $((i*3)) วินาที)"; break
  fi
  [ "$i" = 60 ] && { bad "รอเกิน 180 วินาทีแล้วยังไม่พร้อม"; docker compose ps; docker compose logs --tail 60; }
  sleep 3
done

head "4. ทุก container ต้องอยู่สถานะ running"
docker compose ps
DEAD=$(docker compose ps --format '{{.Service}} {{.State}}' | grep -v ' running$' || true)
if [ -z "$DEAD" ]; then ok "ทุก container running"; else bad "มีตัวที่ไม่ running:"; echo "$DEAD"; fi

check() {  # ชื่อ  url  ข้อความที่ต้องมีในคำตอบ  [วิธี] [body]
  local name="$1" url="$2" want="$3" method="${4:-GET}" body="${5:-}"
  local out
  if [ "$method" = "POST" ]; then
    out=$(curl -fsS --max-time 20 -X POST "$url" -H 'Content-Type: application/json' -d "$body" 2>&1)
  else
    out=$(curl -fsS --max-time 20 "$url" 2>&1)
  fi
  if [ $? -ne 0 ]; then bad "$name — เรียกไม่สำเร็จ: ${out:0:90}"; return; fi
  case "$out" in
    *"$want"*) ok "$name" ;;
    *) bad "$name — ตอบมาแต่ไม่มี '$want' (${out:0:90})" ;;
  esac
}

head "5. ยิง endpoint จริงของแต่ละบริการ"
check "09 หน้าเว็บ"                 "http://localhost:3000/"                       "<!DOCTYPE html"
check "09 /api/courses"             "http://localhost:3000/api/courses?term=1/2569" '"course_code"'
check "09 ตรวจตารางชน"               "http://localhost:3000/api/validate"           '"conflicts"' POST \
      '{"term":"1/2569","section_ids":["04100201-66-01"]}'
check "01 หน้าเว็บ (nginx)"          "http://localhost:3001/"                       "<"
check "02 API Gateway"              "http://localhost:8000/health"                 '"ok"'
check "03 AI Router"                "http://localhost:8100/health"                 '"ok"'
check "04 Course Data"              "http://localhost:8400/health"                 '"ok"'
check "05 Data Integration"         "http://localhost:8500/health"                 '"ok"'
check "06 Schedule Engine"          "http://localhost:8600/health"                 '"ok"'
check "07 RAG + LLM"                "http://localhost:8700/health"                 '"documents"'
check "08 Feedback"                 "http://localhost:8800/health"                 '"ok"'
check "Qdrant (Vector DB)"          "http://localhost:6333/readyz"                 ""
check "Prometheus"                  "http://localhost:9090/-/healthy"              ""
check "Grafana"                     "http://localhost:3002/api/health"             '"database"'

head "6. เรียกข้ามบริการได้จริงไหม"
check "07 ตอบคำถามพร้อมแหล่งอ้างอิง" "http://localhost:8700/generate"               '"sources"' POST \
      '{"question":"ถอนรายวิชาได้ถึงเมื่อไหร่","context":{}}'
# Prometheus ต้อง scrape บริการอื่นได้ = พิสูจน์ว่า container คุยกันในเครือข่ายเดียวกัน
UP=$(curl -fsS --max-time 10 'http://localhost:9090/api/v1/query?query=up' 2>/dev/null | grep -o '"value"' | wc -l)
if [ "${UP:-0}" -gt 0 ]; then ok "Prometheus เห็นบริการอื่นในเครือข่าย ($UP target)"
else bad "Prometheus ยังไม่เห็น target (อาจต้องรอ scrape รอบแรก 15 วินาที)"; fi

head "สรุป"
printf '  ผ่าน %d · ตก %d\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo
  echo "log ของบริการที่มีปัญหา:"
  docker compose logs --tail 40
  echo
  echo "ปิดระบบด้วย: docker compose down"
  exit 1
fi
echo "  ระบบขึ้นครบและใช้งานได้จริง"
echo
echo "  เปิดใช้งาน"
echo "    http://localhost:3000   แอปหลัก (09) จัดตาราง ตรวจชน ถามระเบียบ"
echo "    http://localhost:3001   หน้าเว็บ (01)"
echo "    http://localhost:8700/docs  RAG API (07)"
echo "    http://localhost:9090   Prometheus     http://localhost:3002  Grafana"
echo
echo "  ปิดระบบด้วย: docker compose down"
