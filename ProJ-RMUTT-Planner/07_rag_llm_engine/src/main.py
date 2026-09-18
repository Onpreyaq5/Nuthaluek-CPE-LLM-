"""07_rag_llm_engine — service skeleton (ยังไม่มี logic จริง)"""
from fastapi import FastAPI

app = FastAPI(title="07_rag_llm_engine")


@app.get("/health")
def health():
    return {"ok": True, "service": "07_rag_llm_engine"}
