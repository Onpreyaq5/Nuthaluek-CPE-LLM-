"""กล่อง 4 ในแผนภาพ: Router ต้องเลือก AI ให้ถูกตัว และโมเดลในเครื่องตอบมั่วต้องไม่ทำให้พัง"""
from __future__ import annotations

import json

import pytest

from src import classifier
from src.ai_select import GENERAL_AI, LOCAL_AI, UNIVERSITY_RAG, select_ai
from src.config import settings


@pytest.mark.parametrize("intent", [
    "REGULATION_QA", "CURRICULUM_RULE", "SCHEDULE_CONFLICT", "PLAN_GENERATE", "COURSE_INFO",
])
def test_university_questions_always_go_to_rag(monkeypatch, intent):
    # มีโมเดลไหนพร้อมก็ตาม เรื่องมหาวิทยาลัยต้องยึดเอกสาร/ผลของระบบ
    monkeypatch.setattr(settings, "llm_api_key", "k")
    assert select_ai(intent) == UNIVERSITY_RAG
    monkeypatch.setattr(settings, "llm_api_key", "")
    assert select_ai(intent) == UNIVERSITY_RAG


def test_general_chat_uses_gemini_when_key_present(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "k")
    assert select_ai("GENERAL_CHAT") == GENERAL_AI


def test_general_chat_falls_back_to_local_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "local_model_url", "http://local_ai:11434")
    assert select_ai("GENERAL_CHAT") == LOCAL_AI


def test_local_classifier_result_is_used(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "local_model_url", "http://local_ai:11434")
    monkeypatch.setattr(classifier, "_call_local", lambda prompt: json.dumps(
        {"intent": "regulation_qa", "confidence": 0.8, "reasoning": "asks about withdrawal"}
    ))
    result = classifier._llm_classify("อยากรู้เรื่องถอนวิชา CPE101", [])
    assert result.intent == "REGULATION_QA"
    assert result.source == "local"
    # slot มาจาก regex ไม่ใช่จากโมเดลเล็ก
    assert result.slots == classifier._extract_slots("อยากรู้เรื่องถอนวิชา CPE101")


def test_local_classifier_garbage_falls_back_to_keyword(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "local_model_url", "http://local_ai:11434")
    monkeypatch.setattr(classifier, "_call_local", lambda prompt: '{"intent": "WEATHER"}')
    result = classifier._llm_classify("สวัสดี", [])
    assert result.source == "keyword"
    assert result.intent in result.VALID_INTENTS


def test_no_key_and_no_local_model_uses_keyword(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "local_model_url", "")
    result = classifier._llm_classify("สวัสดี", [])
    assert result.source == "keyword"
