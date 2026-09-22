FROM python:3.11-slim

WORKDIR /app

COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY src/ ./src/
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY entrypoint.sh ./
# กัน CRLF หลุดเข้ามาอีกทาง (เช่นเครื่องที่ clone มาก่อนมี .gitattributes ตัวนี้ หรือ git core.autocrlf
# ของเครื่อง build เป็น true) - ถ้าไม่ตัด \r ออก shebang "#!/bin/sh\r" จะหา interpreter ไม่เจอ
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
