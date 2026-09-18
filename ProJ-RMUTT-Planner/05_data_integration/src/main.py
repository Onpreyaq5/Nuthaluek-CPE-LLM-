"""05_data_integration — service skeleton (ยังไม่มี logic จริง)"""
from fastapi import FastAPI

app = FastAPI(title="05_data_integration")


@app.get("/health")
def health():
    return {"ok": True, "service": "05_data_integration"}
