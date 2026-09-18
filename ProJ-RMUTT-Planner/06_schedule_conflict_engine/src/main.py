"""06_schedule_conflict_engine — service skeleton (ยังไม่มี logic จริง)"""
from fastapi import FastAPI

app = FastAPI(title="06_schedule_conflict_engine")


@app.get("/health")
def health():
    return {"ok": True, "service": "06_schedule_conflict_engine"}
