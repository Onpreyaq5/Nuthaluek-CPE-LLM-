#!/usr/bin/env bash
# ยกระบบทั้งหมดขึ้นด้วย Docker แล้วตรวจให้ครบทุกกล่องและทุกลูกศรในแผนภาพ จบในคำสั่งเดียว
#
#   cd ProJ-RMUTT-Planner
#   bash scripts/verify_docker.sh
#
# ตรวจตามลำดับ
#   1. build ทุกบริการ
#   2. ยกขึ้นแล้วรอจนพร้อม (รวมดึงโมเดล Local AI ครั้งแรก)
#   3. ทุก container ต้องอยู่สถานะ running ไม่มีตัวไหนตายหรือวนรีสตาร์ต
#   4. ยิง endpoint จริงของแต่ละกล่อง
#   5. เดินตามลูกศรในแผนภาพ: หน้าเว็บ -> API -> Router -> AI -> Retrieval -> คำตอบ -> Monitoring
#
# ออกด้วยรหัส 0 เมื่อผ่านหมด ไม่ผ่านจะพิมพ์ log ของตัวที่มีปัญหาให้เลย
#
# คำถามภาษาไทยในสคริปต์เขียนเป็น \uXXXX ใน JSON ตั้งใจ:
# curl บน Windows (Git Bash) ส่งอาร์กิวเมนต์ภาษาไทยเป็น codepage ของเครื่อง ไม่ใช่ UTF-8
# JSON จะพังและได้ 400 ทั้งที่ระบบถูก แบบ \u ใช้ได้เหมือนกันทุกเครื่อง
set -uo pipefail
cd "$(dirname "$0")/.."

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  \033[32mผ่าน\033[0m  %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  \033[31mตก\033[0m    %s\n' "$1"; }
head() { printf '\n\033[1m%s\033[0m\n' "$1"; }
note() { printf '        %s\n' "$1"; }

Q_WITHDRAW='ถอนรายวิชาได้ถึงเมื่อไหร่'   # ถอนรายวิชาได้ถึงเมื่อไหร่
Q_HELLO='สวัสดีครับ ช่วยแนะนำตัวสั้นๆ หน่อย'  # สวัสดีครับ ช่วยแนะนำตัวสั้นๆ หน่อย
Q_COFFEE='แนะนำร้านกาแฟหน่อย'  # แนะนำร้านกาแฟหน่อย

[ -f .env ] || { echo "ยังไม่มี .env — คัดลอกจากตัวอย่างให้แล้ว"; cp .env.example .env; }
LOCAL_MODEL=$(grep -E '^LOCAL_MODEL=' .env 2>/dev/null | cut -d= -f2-); LOCAL_MODEL=${LOCAL_MODEL:-qwen2.5:0.5b}

head "1. build ทุกบริการ"
if docker compose build; then ok "build ผ่านทุกบริการ"; else
  bad "build ไม่ผ่าน"; echo; echo "หยุดตรงนี้ เพราะไม่มีอะไรให้รันต่อ"; exit 1
fi

head "2. ยกระบบขึ้น"
docker compose up -d || { bad "docker compose up ไม่สำเร็จ"; docker compose logs --tail 80; exit 1; }
ok "สั่งขึ้นแล้ว"

wait_for() {  # ชื่อ  วินาทีสูงสุด  คำสั่งตรวจ...
  local name="$1" max="$2"; shift 2
  local t=0
  until "$@" >/dev/null 2>&1; do
    t=$((t+3))
    if [ "$t" -ge "$max" ]; then bad "$name — รอเกิน $max วินาทีแล้วยังไม่พร้อม"; return 1; fi
    sleep 3
  done
  ok "$name พร้อม (${t} วินาที)"
}

head "3. รอให้ทุกกล่องพร้อม"
wait_for "หน้าเว็บหลัก (09)"       180 curl -fsS --max-time 3 http://localhost:3000/
wait_for "RAG + LLM (07)"          180 curl -fsS --max-time 3 http://localhost:8700/health
wait_for "API Gateway (02)"        180 curl -fsS --max-time 3 http://localhost:8000/health
wait_for "หน้าเว็บ 01 (nginx)"      180 curl -fsS --max-time 3 http://localhost:3001/
wait_for "Grafana"                 180 curl -fsS --max-time 3 http://localhost:3002/api/health
# ครั้งแรกต้องดาวน์โหลดโมเดล ~400 MB ครั้งต่อไปอยู่ใน volume แล้ว
wait_for "Local AI มีโมเดล $LOCAL_MODEL" 900 sh -c \
  "curl -fsS --max-time 5 http://localhost:11434/api/tags | grep -q '\"${LOCAL_MODEL%%:*}'"

head "4. ทุก container ต้องอยู่สถานะ running"
docker compose ps
# local_ai_pull ตั้งใจให้จบหลังดึงโมเดลเสร็จ ต้องจบด้วยรหัส 0
DEAD=$(docker compose ps -a --format '{{.Service}} {{.State}}' | grep -v '^local_ai_pull ' | grep -v ' running$' || true)
if [ -z "$DEAD" ]; then ok "ทุก container running"; else bad "มีตัวที่ไม่ running:"; echo "$DEAD"; fi
PULL_EXIT=$(docker inspect -f '{{.State.ExitCode}}' rmutt_local_ai_pull 2>/dev/null || echo "?")
[ "$PULL_EXIT" = "0" ] && ok "ดึงโมเดล Local AI สำเร็จ (exit 0)" || bad "ดึงโมเดล Local AI ไม่สำเร็จ (exit $PULL_EXIT)"

BODY_FILE=$(mktemp); trap 'rm -f "$BODY_FILE"' EXIT
check() {  # ชื่อ  url  ข้อความที่ต้องมีในคำตอบ  [วิธี] [body] [timeout]
  local name="$1" url="$2" want="$3" method="${4:-GET}" body="${5:-}" tmo="${6:-20}"
  local out rc
  if [ "$method" = "POST" ]; then
    # ส่ง body ผ่านไฟล์ ไม่ใช่ -d "..." : curl บน Git Bash (Windows) ทำ body ที่ส่งเป็นอาร์กิวเมนต์พัง
    # ได้ 400 "error parsing the body" ทั้งที่ JSON ถูก ส่งผ่านไฟล์ได้ผลเหมือนกันทุกเครื่อง
    printf '%s' "$body" > "$BODY_FILE"
    out=$(curl -fsS --max-time "$tmo" -X POST "$url" -H 'Content-Type: application/json' \
          --data-binary "@$BODY_FILE" 2>&1); rc=$?
  else
    out=$(curl -fsS --max-time "$tmo" "$url" 2>&1); rc=$?
  fi
  if [ $rc -ne 0 ]; then bad "$name — เรียกไม่สำเร็จ: ${out:0:120}"; return 1; fi
  case "$out" in
    *"$want"*) ok "$name"; LAST="$out"; return 0 ;;
    *) bad "$name — ตอบมาแต่ไม่มี '$want' (${out:0:160})"; return 1 ;;
  esac
}

head "5. ยิง endpoint จริงของแต่ละกล่องในแผนภาพ"
check "1 Web App (09)"                  "http://localhost:3000/"                         "<!DOCTYPE html"
check "1 Web App (01 ผ่าน nginx)"       "http://localhost:3001/"                         "<"
check "2 API / Backend (02)"            "http://localhost:8000/health"                   '"ok"'
check "3 AI Router / Agent (03)"        "http://localhost:8100/health"                   '"ok"'
check "4 University RAG (07)"           "http://localhost:8700/health"                   '"documents"'
check "4 Local AI Model (Ollama)"       "http://localhost:11434/api/tags"                "${LOCAL_MODEL%%:*}"
check "5 Retrieval ใช้ Vector DB จริง"   "http://localhost:8700/health"                   '"vector_backend":"qdrant"'
check "5 Qdrant มีเวกเตอร์เอกสาร"        "http://localhost:6333/collections/rmutt_knowledge" '"points_count"'
check "   Course Data (04)"             "http://localhost:8400/health"                   '"ok"'
check "   Data Integration (05)"        "http://localhost:8500/health"                   '"ok"'
check "   Schedule Engine (06)"         "http://localhost:8600/health"                   '"ok"'
check "7 Response / Log (08)"           "http://localhost:8800/health"                   '"ok"'
check "   Monitoring: Prometheus"       "http://localhost:9090/-/healthy"                ""
check "   Monitoring: Grafana"          "http://localhost:3002/api/health"               '"database"'
check "   09 /api/courses"              "http://localhost:3000/api/courses?term=1/2569"  '"course_code"'
check "   09 ตรวจตารางชน"                "http://localhost:3000/api/validate"             '"conflicts"' POST \
      '{"term":"1/2569","section_ids":["04100201-66-01"]}'

head "6. เดินตามลูกศรในแผนภาพ"

# กล่อง 3 -> 4: Router เลือก AI
check "3→4 Router ส่งคำถามระเบียบไป University RAG" "http://localhost:8100/chat" '"ai_target": "university_rag"' POST \
      "{\"student_id\":\"6500000000\",\"session_id\":\"verify\",\"message\":\"$Q_WITHDRAW\"}" 30
check "3→4 Router ส่งคำทักทายไป General/Local AI"   "http://localhost:8100/chat" '"ai_target": "' POST \
      "{\"student_id\":\"6500000000\",\"session_id\":\"verify\",\"message\":\"$Q_HELLO\"}" 30
case "${LAST:-}" in
  *'"ai_target": "local_ai"'*)   note "ไม่มีคีย์ Gemini -> งานทั่วไปตกไปที่ Local AI ในเครื่อง (ตามออกแบบ)";;
  *'"ai_target": "general_ai"'*) note "มีคีย์ Gemini -> งานทั่วไปไปที่ General AI";;
esac

# กล่อง 5 -> 6: ค้นแล้วสร้างคำตอบพร้อมแหล่งอ้างอิง
check "5→6 RAG ตอบพร้อมแหล่งอ้างอิง"   "http://localhost:8700/generate" '"grounded":true' POST \
      "{\"question\":\"$Q_WITHDRAW\",\"context\":{}}"
check "5→6 เรื่องนอกเอกสาร ต้องปฏิเสธ"  "http://localhost:8700/generate" '"grounded":false' POST \
      "{\"question\":\"$Q_COFFEE\",\"context\":{}}"
# โมเดลในเครื่องบน CPU อาจใช้เวลาหลายสิบวินาที ครั้งแรกต้องโหลดโมเดลเข้าหน่วยความจำก่อน
check "4→6 Local AI ตอบคำถามทั่วไปได้จริง" "http://localhost:8700/generate" '"provider":"' POST \
      "{\"question\":\"$Q_HELLO\",\"context\":{\"ai_target\":\"local_ai\"}}" 180
case "${LAST:-}" in
  *'"provider":"local:'*|*'"provider":"gemini"'*) ok "   คำตอบมาจากโมเดลจริง ไม่ใช่ข้อความสำรอง";;
  *) bad "   Local AI ไม่ได้ตอบ (${LAST:0:160})";;
esac

# กล่อง 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7: login แล้วแชตผ่านหน้าเว็บ 01 จริง
JAR=$(mktemp); CHAT=$(mktemp)
if curl -fsS --max-time 10 -c "$JAR" -X POST http://localhost:3001/api/v1/auth/login \
     -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin1234"}' >/dev/null 2>&1; then
  ok "1→2 login ผ่านหน้าเว็บ 01 (บัญชีเดโมถูกสร้างแล้ว)"
  printf '%s' "{\"message\":\"$Q_WITHDRAW\"}" > "$BODY_FILE"
  curl -sS -N --max-time 180 -b "$JAR" -X POST http://localhost:3001/api/v1/chat \
       -H 'Content-Type: application/json' --data-binary "@$BODY_FILE" > "$CHAT" 2>&1
  if grep -q '"type": "done"' "$CHAT" && grep -q '"type": "token"' "$CHAT"; then
    ok "1→7 แชตครบสาย: หน้าเว็บ→API→Router→RAG→คำตอบ"
    grep -q '"type": "sources"' "$CHAT" && ok "   คำตอบแนบแหล่งอ้างอิงกลับมาถึงหน้าเว็บ" \
                                        || bad "   ไม่มีแหล่งอ้างอิงในคำตอบ"
  else
    bad "1→7 แชตไม่ครบสาย ($(tr '\n' ' ' < "$CHAT" | cut -c1-200))"
  fi
else
  bad "1→2 login ไม่ได้ (ตรวจว่า SEED_DEMO=true)"
fi
rm -f "$JAR" "$CHAT"

# กล่อง 2 <-> User Data: ประวัติแชตถูกบันทึกลง Postgres จริง
ROWS=$(docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select count(*) from chat_messages"' 2>/dev/null | tr -d '[:space:]')
if [ "${ROWS:-0}" -gt 0 ] 2>/dev/null; then ok "2↔User Data บันทึกประวัติแชตใน Postgres ($ROWS ข้อความ)"
else bad "2↔User Data ไม่พบประวัติแชตใน Postgres (${ROWS:-อ่านไม่ได้})"; fi

# กล่อง 7 <-> Monitoring: Prometheus ต้องเก็บตัวเลขได้จากทุกบริการ
sleep 16   # รอ scrape รอบถัดไปให้เห็นตัวเลขจากการยิงข้างบน
TARGETS=$(curl -fsS --max-time 10 'http://localhost:9090/api/v1/targets?state=active' 2>/dev/null)
UP=$(printf '%s' "$TARGETS" | grep -o '"health":"up"' | wc -l | tr -d ' ')
DOWN=$(printf '%s' "$TARGETS" | grep -o '"health":"down"' | wc -l | tr -d ' ')
if [ "${UP:-0}" -gt 0 ] && [ "${DOWN:-1}" -eq 0 ]; then ok "7↔Monitoring Prometheus เก็บจากทุกบริการ ($UP target, ล่ม 0)"
else bad "7↔Monitoring มี target ล่ม $DOWN จาก $((UP+DOWN)) — ดูที่ http://localhost:9090/targets"; fi
check "7↔Monitoring Prometheus นับว่า Router เลือก AI ไหน" \
      'http://localhost:9090/api/v1/query?query=sum%20by%20(ai_target)%20(rmutt_router_routed_total)' '"ai_target"'
check "7↔Monitoring Grafana มี dashboard พร้อมใช้" \
      "http://localhost:3002/api/dashboards/uid/rmutt-overview" '"rmutt-overview"'

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
echo "  ระบบขึ้นครบทุกกล่องและทุกลูกศรในแผนภาพ ใช้งานได้จริง"
echo
echo "  เปิดใช้งาน"
echo "    http://localhost:3000   แอปหลัก (09) จัดตาราง ตรวจชน ถามระเบียบ"
echo "    http://localhost:3001   หน้าเว็บ (01) login admin / admin1234 แล้วแชตผ่านสายเต็ม"
echo "    http://localhost:8700/docs   RAG API (07)      http://localhost:8100/docs  AI Router (03)"
echo "    http://localhost:6333/dashboard   Qdrant       http://localhost:9090  Prometheus"
echo "    http://localhost:3002   Grafana (dashboard ภาพรวมระบบ เปิดดูได้โดยไม่ต้อง login)"
echo
echo "  ปิดระบบด้วย: docker compose down"
