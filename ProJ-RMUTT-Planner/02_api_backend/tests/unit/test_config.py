from __future__ import annotations

from src.core.config import Settings

_DEFAULT_ROUTER_URL = "http://ai_router:8100"


def test_router_url_default_is_ai_router_8100() -> None:
    settings = Settings(_env_file=None)
    assert settings.ROUTER_URL == _DEFAULT_ROUTER_URL


def test_router_url_reads_from_ai_router_url_env(monkeypatch) -> None:
    monkeypatch.setenv("AI_ROUTER_URL", "http://ai_router:9999")
    monkeypatch.delenv("ROUTER_URL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.ROUTER_URL == "http://ai_router:9999"


def test_router_url_falls_back_to_router_url_env(monkeypatch) -> None:
    monkeypatch.delenv("AI_ROUTER_URL", raising=False)
    monkeypatch.setenv("ROUTER_URL", "http://legacy-router:8001")
    settings = Settings(_env_file=None)
    assert settings.ROUTER_URL == "http://legacy-router:8001"


def test_router_url_prefers_ai_router_url_when_both_set(monkeypatch) -> None:
    monkeypatch.setenv("AI_ROUTER_URL", "http://ai_router:8100")
    monkeypatch.setenv("ROUTER_URL", "http://legacy-router:8001")
    settings = Settings(_env_file=None)
    assert settings.ROUTER_URL == "http://ai_router:8100"


def test_tool_allowlist_matches_real_03_tool_registry() -> None:
    settings = Settings(_env_file=None)
    assert settings.tool_allowlist_set == {
        "search_courses",
        "get_student_context",
        "check_conflicts",
        "generate_plan",
        "search_knowledge",
        "answer_with_llm",
    }
