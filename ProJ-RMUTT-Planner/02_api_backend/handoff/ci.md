# ข้อเสนอ: เพิ่ม job `api-backend` ใน `.github/workflows/ci.yml` (root)

โมดูล `02_api_backend` แก้ `.github/workflows/ci.yml` เองไม่ได้ (CLAUDE.md ข้อ 12) — เอกสารนี้เป็น
**ข้อเสนอ** YAML เต็มให้ทีมที่ดูแล CI นำไปเพิ่มเป็น job ใหม่ (ไม่แก้ matrix เดิม)

## YAML ที่เสนอ

```yaml
  api-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: rmutt
          POSTGRES_PASSWORD: change_me_please
          POSTGRES_DB: rmutt_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U rmutt -d rmutt_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        working-directory: 02_api_backend
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint
        working-directory: 02_api_backend
        run: ruff check .

      - name: Test
        working-directory: 02_api_backend
        env:
          TEST_DATABASE_URL: postgresql+psycopg://rmutt:change_me_please@localhost:5432/rmutt_test
        run: pytest -q
```

## หมายเหตุ

- job syntax-check เดิม (ที่ทำ `compileall` กับ pattern `0*/src`) ครอบ `02_api_backend` อยู่แล้วโดยอัตโนมัติ
  เพราะโมดูลนี้ใช้ `src/` ตรงกับ pattern เดิมพอดี ไม่ต้องแก้ตรงนั้น
- **สำคัญ:** เจตนาให้ `02_api_backend` เป็น job แยกต่างหาก **ไม่ใช่แค่เพิ่มชื่อเข้า matrix ของ job
  `python-tests` เดิม** เพราะ matrix เดิมติดตั้งด้วย `pip install -r requirements.txt pytest` (บรรทัดเดียว
  ไม่มี `requirements-dev.txt`) — ของ 02 แยก dev deps (`pytest-asyncio`, `fakeredis`, `ruff`) ไว้ใน
  `requirements-dev.txt` ต่างหากจาก `requirements.txt` (prod-only) ถ้าเพิ่ม `02_api_backend` เข้า matrix
  เดิมตรงๆ จะ **พังทันทีที่ `import fakeredis`** ใน `tests/conftest.py` (autouse fixture ทุกเทสต์) ทั้งที่
  โค้ดไม่มีปัญหาอะไรเลย — job แยกด้านบนนี้แก้ปัญหานี้แล้วด้วยการ `pip install` ทั้งสองไฟล์แยกกัน
- **ตอนนี้ CI ยังไม่รัน test ของ `02_api_backend` เลย** จนกว่าทีมจะรับข้อเสนอนี้เข้า `ci.yml` จริง —
  ระหว่างรอ ให้รัน `sh 02_api_backend/scripts/test.sh` เองก่อน push (ดูรายละเอียดใน PROGRESS.md)
- ทดสอบ pattern connection string และ health-check ของ service `postgres` นี้แล้วกับ Postgres จริง
  (ตัวเดียวกับที่ใช้ยืนยัน Prompt 4) ใช้งานได้ปกติ
