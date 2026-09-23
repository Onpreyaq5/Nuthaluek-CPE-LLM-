"""config.py — Settings loaded from environment variables (.env)"""
import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM Provider: gemini | openai | anthropic | groq
    llm_provider: str = "gemini"
    llm_api_key: str = ""
    llm_model: str = "gemini-flash-lite-latest"

    # Local AI Model (Ollama) — ช่อง Local AI ในแผนภาพ
    # ใช้จัดประเภทคำถามตอน keyword ไม่มั่นใจ เมื่อไม่มีคีย์ของ provider ภายนอก
    local_model: str = "qwen2.5:0.5b"
    # ต้องน้อยกว่า TIMEOUT_CHAT_START_SECONDS ของ 02 (15 วินาที) ไม่งั้น 02 ตัดว่า 03 ไม่ตอบ
    local_classify_timeout_s: float = 10.0

    # Internal service URLs (Docker Compose hostnames)
    local_model_url: str = "http://local_ai:11434"              # Ollama ฟังที่ 11434 ไม่ใช่ 8300
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

    @model_validator(mode="after")
    def _key_fallback(self) -> "Settings":
        # .env ของโปรเจกต์ใส่คีย์ Gemini ไว้ที่ GEMINI_API_KEY (ใช้ร่วมกับ 09)
        # ผู้ใช้จึงใส่คีย์ที่เดียวแล้วใช้ได้ทั้งระบบ
        if not self.llm_api_key and self.llm_provider.lower() == "gemini":
            self.llm_api_key = os.getenv("GEMINI_API_KEY", "")
        return self


settings = Settings()
