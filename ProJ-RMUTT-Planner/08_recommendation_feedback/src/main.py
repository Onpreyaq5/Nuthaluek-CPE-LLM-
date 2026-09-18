"""08_recommendation_feedback — service skeleton (ยังไม่มี logic จริง)"""
from fastapi import FastAPI

app = FastAPI(title="08_recommendation_feedback")


@app.get("/health")
def health():
    return {"ok": True, "service": "08_recommendation_feedback"}
