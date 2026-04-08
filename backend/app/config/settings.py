from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MindEase Backend"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "mindease"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    hf_api_token: str = ""
    hf_model: str = "google/flan-t5-large"
    hf_text_emotion_model: str = "SamLowe/roberta-base-go_emotions"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    gpt4all_model_path: str = ""
    
    groq_api_key: str = ""

    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173,http://localhost:8080")
    cors_origin_regex: str = (
        r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?$"
    )
    rate_limit_per_minute: int = 60

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
