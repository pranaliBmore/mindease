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

    # Signup verification email. Two ways to send, see app/services/email_service.py:
    # - EMAIL_RELAY_URL set (production): POST to the Netlify Function that sends via
    #   Gmail with Nodemailer - Render's free plan blocks outbound SMTP, Netlify doesn't.
    # - otherwise SMTP below, sent directly with Python's smtplib (local dev).
    # Neither configured = dev fallback: the OTP is logged instead of emailed.
    email_relay_url: str = ""
    email_relay_secret: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "MindEase"
    smtp_use_tls: bool = True


    otp_expire_minutes: int = 10
    otp_length: int = 6
    otp_max_attempts: int = 5
    # New accounts must confirm a 6-digit OTP emailed to them (Netlify relay or SMTP, see
    # email_service). Set REQUIRE_EMAIL_VERIFICATION=false only as an emergency kill
    # switch if email delivery breaks - accounts are then marked verified on signup.
    require_email_verification: bool = True

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
