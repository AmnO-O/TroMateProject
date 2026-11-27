from __future__ import annotations

import re
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


ENV_CONFIG = SettingsConfigDict(
    env_file=BACKEND_DIR / ".env",
    env_file_encoding="utf-8",
    extra="ignore",
    case_sensitive=False,
)


class DatabaseSettings(BaseSettings):
    """Database settings only.

    Alembic and ``app.db`` load this class instead of :class:`Settings`, so running a
    migration does not require Telegram credentials.
    """

    model_config = ENV_CONFIG

    # Neon connection string, e.g. postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
    # Plain ``postgresql://`` URLs are converted to the asyncpg driver in ``app.db.session``.
    database_url: str = ""
    database_echo: bool = False
    database_pool_size: int = Field(default=5, gt=0)
    database_max_overflow: int = Field(default=5, ge=0)

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        return value.strip()


AppEnv = Literal["local", "test", "production"]

# BR10: voting periods the Room Rep can choose when opening a vote (UC13).
REP_VOTE_PERIOD_CHOICES_HOURS: tuple[int, ...] = (12, 24, 48, 72)


class DurationSettings(BaseSettings):
    """Time durations of Use-Case Specification v3.0, in minutes (SCRUM-138).

    Defaults are the production values. The shared test environment overrides them in
    ``.env`` (Test Plan v1.2, section 3) so time-based flows can be tested in minutes.
    With ``APP_ENV=production`` every value must equal its default, or settings fail to load
    and the app refuses to start.

    Like :class:`DatabaseSettings`, this class needs no Telegram credentials, so services and
    tests can load it on its own.
    """

    model_config = ENV_CONFIG

    app_env: AppEnv = "local"

    # BR03, UC13-AF05: allowed range of the room's auto-confirmation window.
    review_window_min_minutes: int = Field(default=24 * 60, gt=0)
    review_window_max_minutes: int = Field(default=30 * 24 * 60, gt=0)
    # BR10: when set, replaces every period the Room Rep can choose (12/24/48/72 hours).
    # Unset in production, where the chosen period is used.
    rep_vote_period_minutes: int | None = Field(default=None, gt=0)
    # BR11: voting period opened by a change request.
    change_request_vote_period_minutes: int = Field(default=24 * 60, gt=0)
    # BR10: reminder sent this long before a vote ends.
    vote_reminder_before_end_minutes: int = Field(default=2 * 60, gt=0)
    # BR11, UC15-AF06: how long a change request stays open.
    change_request_open_period_minutes: int = Field(default=3 * 24 * 60, gt=0)
    # BR11, UC15-AF04: cooldown between change requests or votes.
    proposal_cooldown_minutes: int = Field(default=7 * 24 * 60, gt=0)
    # BR04, UC05-AF02: interval between reminders for a Disputed expense.
    dispute_reminder_interval_minutes: int = Field(default=3 * 24 * 60, gt=0)
    # BR03, UC06-AF05: reminder sent this long before an auto-confirmation deadline ...
    deadline_reminder_before_minutes: int = Field(default=24 * 60, gt=0)
    # ... only when the expense's window is longer than this.
    deadline_reminder_min_window_minutes: int = Field(default=24 * 60, gt=0)

    @model_validator(mode="after")
    def validate_durations(self) -> DurationSettings:
        if self.review_window_min_minutes > self.review_window_max_minutes:
            raise ValueError("REVIEW_WINDOW_MIN_MINUTES must not exceed REVIEW_WINDOW_MAX_MINUTES")
        if self.app_env == "production":
            changed = self.non_production_durations()
            if changed:
                details = ", ".join(
                    f"{name.upper()}={value} (production: {expected})"
                    for name, (value, expected) in changed.items()
                )
                raise ValueError(
                    "APP_ENV=production requires production time durations; "
                    f"remove these overrides: {details}"
                )
        return self

    @classmethod
    def duration_field_names(cls) -> tuple[str, ...]:
        return tuple(name for name in DurationSettings.model_fields if name != "app_env")

    def duration_values(self) -> dict[str, int | None]:
        """Active duration settings, for the startup log."""

        return {name: getattr(self, name) for name in self.duration_field_names()}

    def non_production_durations(self) -> dict[str, tuple[int | None, int | None]]:
        """Durations that differ from production, as ``{name: (value, default)}``."""

        fields = DurationSettings.model_fields
        return {
            name: (value, fields[name].default)
            for name, value in self.duration_values().items()
            if value != fields[name].default
        }

    def rep_vote_period(self, chosen_hours: int) -> timedelta:
        """Voting period for a Room Rep vote opened with ``chosen_hours`` (BR10)."""

        if chosen_hours not in REP_VOTE_PERIOD_CHOICES_HOURS:
            raise ValueError(f"Voting period must be one of {REP_VOTE_PERIOD_CHOICES_HOURS} hours")
        if self.rep_vote_period_minutes is not None:
            return timedelta(minutes=self.rep_vote_period_minutes)
        return timedelta(hours=chosen_hours)

    @property
    def change_request_vote_period(self) -> timedelta:
        return timedelta(minutes=self.change_request_vote_period_minutes)

    @property
    def vote_reminder_before_end(self) -> timedelta:
        return timedelta(minutes=self.vote_reminder_before_end_minutes)

    @property
    def change_request_open_period(self) -> timedelta:
        return timedelta(minutes=self.change_request_open_period_minutes)

    @property
    def proposal_cooldown(self) -> timedelta:
        return timedelta(minutes=self.proposal_cooldown_minutes)

    @property
    def dispute_reminder_interval(self) -> timedelta:
        return timedelta(minutes=self.dispute_reminder_interval_minutes)

    @property
    def deadline_reminder_before(self) -> timedelta:
        return timedelta(minutes=self.deadline_reminder_before_minutes)

    def needs_deadline_reminder(self, window_minutes: int | None) -> bool:
        """Whether an expense with this window gets a reminder before its deadline (UC06-AF05)."""

        return (
            window_minutes is not None
            and window_minutes > self.deadline_reminder_min_window_minutes
        )


class Settings(DatabaseSettings, DurationSettings):
    """Application settings loaded from environment variables and ``.env``."""

    app_env: AppEnv = "local"
    log_level: str = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000

    public_base_url: str = ""
    bot_library: Literal["ptb", "aiogram", "telebot"] = "aiogram"

    telegram_bot_token: str
    telegram_webhook_secret: str
    telegram_webhook_path: str = "/webhook/telegram"
    auto_set_webhook: bool = True

    miniapp_initdata_max_age_seconds: int = Field(default=3600, gt=0)
    miniapp_initdata_max_length: int = Field(default=8192, gt=0)
    miniapp_max_body_bytes: int = Field(default=1_048_576, gt=0)

    # Google Gemini (AI Extraction Adapter). Empty means the rule-based VND parser fallback is used.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"

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


@lru_cache(maxsize=1)
def get_duration_settings() -> DurationSettings:
    """Return the process-wide duration settings instance."""

    return DurationSettings()


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    """Return the process-wide database settings instance."""

    return DatabaseSettings()
