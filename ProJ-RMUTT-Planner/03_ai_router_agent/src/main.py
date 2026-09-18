"""03_ai_router_agent — service skeleton (ยังไม่มี logic จริง)"""
from fastapi import FastAPI

app = FastAPI(title="03_ai_router_agent")


@app.get("/health")
def health():
    return {"ok": True, "service": "03_ai_router_agent"}
