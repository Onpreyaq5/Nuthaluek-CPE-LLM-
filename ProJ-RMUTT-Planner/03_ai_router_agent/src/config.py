"""config.py — Settings loaded from environment variables (.env)"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM Provider: gemini | openai | anthropic | groq
    llm_provider: str = "gemini"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.0-flash"

    # Internal service URLs (Docker Compose hostnames)
    local_model_url: str = "http://local_ai:8300"               # cheap classify
    course_data_url: str = "http://course_data:8400"            # module 04
    data_integration_url: str = "http://data_integration:8500"  # module 05
    schedule_engine_url: str = "http://schedule_engine:8600"    # module 06
    rag_llm_url: str = "http://rag_llm:8700"                    # module 07

    # Agent behaviour
    max_tool_steps: int = 5
    max_context_tokens: int = 4000
    tool_timeout_s: float = 8.0
    confidence_threshold: float = 0.7   # below this -> call LLM classifier

    log_level: str = "INFO"


settings = Settings()
