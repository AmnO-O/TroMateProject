# ruff: noqa: E402
from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-secret-0123456789abcdef")
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")
os.environ.setdefault("BOT_LIBRARY", "ptb")
os.environ.setdefault("AUTO_SET_WEBHOOK", "false")

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.bots.base import BotEngine
from app.core.config import Settings
from app.main import create_app
from tests.helpers import TEST_BOT_TOKEN, TEST_WEBHOOK_SECRET


class FakeEngine(BotEngine):
    name = "fake"

    def __init__(self) -> None:
        self.username = "fake_bot"
        self.started = False
        self.stopped = False
        self.updates: list[dict[str, Any]] = []

    async def startup(self) -> None:
        self.started = True

    async def shutdown(self) -> None:
        self.stopped = True

    async def handle_update(self, payload: dict[str, Any]) -> None:
        self.updates.append(payload)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test",
        public_base_url="http://testserver",
        auto_set_webhook=False,
        bot_library="ptb",
        telegram_bot_token=TEST_BOT_TOKEN,
        telegram_webhook_secret=TEST_WEBHOOK_SECRET,
    )


@pytest.fixture
def fake_engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def app(settings: Settings, fake_engine: FakeEngine):
    return create_app(settings=settings, engine=fake_engine)


@pytest.fixture
async def client(app):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
            yield http_client


@pytest.fixture
def webhook_headers(settings: Settings) -> dict[str, str]:
    return {
        "X-Telegram-Bot-Api-Secret-Token": settings.telegram_webhook_secret,
        "Content-Type": "application/json",
    }
