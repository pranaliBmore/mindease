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
    groq_model: str = "openai/gpt-oss-20b"

    # Fernet key (urlsafe base64, 32 bytes). Blank = private text is stored as plaintext.
    data_encryption_key: str = ""

    # SMTP (used to email signup verification codes). Blank host = dev fallback:
    # the OTP is logged instead of emailed, so local dev needs no mail account.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "MindEase"
    smtp_use_tls: bool = True

    # Brevo HTTP email API (https://app.brevo.com/settings/keys/api) - sends over HTTPS,
    # so it works on hosts (e.g. Render) that block outbound SMTP. Takes priority over
    # SMTP above when set; SMTP stays as the local-dev path since it works fine there.
    brevo_api_key: str = ""

    otp_expire_minutes: int = 10
    otp_length: int = 6
    otp_max_attempts: int = 5
    # Temporary kill switch while Brevo/SMTP email delivery is unresolved in production -
    # new accounts are marked verified immediately, no OTP generated or sent. Flip back to
    # true once email sending is confirmed working.
    require_email_verification: bool = False

    avatar_upload_dir: str = "uploads/avatars"
    avatar_max_bytes: int = 5 * 1024 * 1024

    cors_origins: str = Field(default="http://localhost:3000,http://localhost:5173,http://localhost:8080")
    cors_origin_regex: str = (
        r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?$"
    )
    rate_limit_per_minute: int = 60
    rate_limit_auth_per_minute: int = 10

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
