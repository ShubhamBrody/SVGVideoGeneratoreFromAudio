"""Application settings loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ----- LLM -----
    llm_provider: str = "auto"  # auto | openai | ollama | mock
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = ""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    llm_temperature: float = 0.3
    llm_timeout: float = 60.0
    llm_max_tokens: int = 1536
    ollama_keep_alive: str = "30m"

    # ----- Speech-to-text -----
    whisper_model: str = "base"
    whisper_device: str = "auto"
    whisper_compute_type: str = "int8"

    # ----- Server -----
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    assets_dir: str = "assets"
    max_upload_mb: int = 25

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
