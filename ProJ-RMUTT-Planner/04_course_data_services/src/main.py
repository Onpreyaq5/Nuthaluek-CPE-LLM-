"""04_course_data_services — service skeleton (ยังไม่มี logic จริง)"""
from fastapi import FastAPI

app = FastAPI(title="04_course_data_services")


@app.get("/health")
def health():
    return {"ok": True, "service": "04_course_data_services"}
