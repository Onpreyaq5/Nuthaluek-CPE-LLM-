"""02_api_backend — service skeleton (ยังไม่มี logic จริง)"""
from fastapi import FastAPI

app = FastAPI(title="02_api_backend")


@app.get("/health")
def health():
    return {"ok": True, "service": "02_api_backend"}
