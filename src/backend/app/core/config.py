from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000

    public_base_url: str = ""
    bot_library: Literal["ptb", "aiogram", "telebot"] = "ptb"

    telegram_bot_token: str
    telegram_webhook_secret: str
    telegram_webhook_path: str = "/webhook/telegram"
    auto_set_webhook: bool = True

    miniapp_initdata_max_age_seconds: int = Field(default=3600, gt=0)
    miniapp_initdata_max_length: int = Field(default=8192, gt=0)
    miniapp_max_body_bytes: int = Field(default=1_048_576, gt=0)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("public_base_url")
    @classmethod
    def normalize_public_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("PUBLIC_BASE_URL must start with http:// or https://")
        return value

    @field_validator("telegram_bot_token")
    @classmethod
    def validate_bot_token(cls, value: str) -> str:
        value = value.strip()
        if ":" not in value or value.startswith(":") or value.endswith(":"):
            raise ValueError("TELEGRAM_BOT_TOKEN must look like <bot_id>:<secret>")
        return value

    @field_validator("telegram_webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, value: str) -> str:
        value = value.strip()
        if not 16 <= len(value) <= 256:
            raise ValueError("TELEGRAM_WEBHOOK_SECRET must be 16-256 characters")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("TELEGRAM_WEBHOOK_SECRET may only contain A-Z, a-z, 0-9, _ and -")
        return value

    @field_validator("telegram_webhook_path")
    @classmethod
    def validate_webhook_path(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            raise ValueError("TELEGRAM_WEBHOOK_PATH must start with /")
        if value != "/":
            value = value.rstrip("/")
        return value

    @model_validator(mode="after")
    def validate_environment(self) -> Settings:
        if self.app_env != "test":
            if self.auto_set_webhook and not self.public_base_url:
                raise ValueError("PUBLIC_BASE_URL is required when AUTO_SET_WEBHOOK=true")
            if self.public_base_url and not self.public_base_url.startswith("https://"):
                raise ValueError("PUBLIC_BASE_URL must use https outside the test environment")
        return self

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url}{self.telegram_webhook_path}"

    @property
    def miniapp_url(self) -> str:
        return f"{self.public_base_url}/miniapp"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings instance."""

    return Settings()
