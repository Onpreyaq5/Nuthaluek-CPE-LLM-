FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 TZ=Asia/Bangkok

RUN apt-get update && apt-get install -y --no-install-recommends       build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

EXPOSE 8500
HEALTHCHECK --interval=30s --timeout=5s --retries=3   CMD curl -fsS http://localhost:8500/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8500"]
