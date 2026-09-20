#!/bin/sh
# entrypoint ของ container api_backend: migrate -> seed (ถ้าสั่ง) -> uvicorn
set -e

alembic upgrade head

if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "SEED_DEMO=true -> รัน scripts/seed_demo.py"
  python -m scripts.seed_demo
fi

exec uvicorn src.main:app --host 0.0.0.0 --port 8000
