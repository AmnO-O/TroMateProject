from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse

from app.api import health, mini_app
from app.api.webhook import create_router as create_webhook_router
from app.bots.base import BotEngine
from app.bots.factory import create_engine
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine, warmup_engine
from app.services.balance_service import BalanceService

WEB_DIR = Path(__file__).resolve().parent / "web"

logger = logging.getLogger(__name__)


def log_duration_settings(settings: Settings) -> None:
    """Log the active time durations (SCRUM-138), flagging any non-production value."""

    values = " ".join(f"{name}={value}" for name, value in settings.duration_values().items())
    logger.info("Duration settings (minutes, APP_ENV=%s): %s", settings.app_env, values)
    changed = settings.non_production_durations()
    if changed:
        logger.warning(
            "Non-production durations in effect: %s", ", ".join(name.upper() for name in changed)
        )


async def miniapp_page() -> FileResponse:
    return FileResponse(WEB_DIR / "miniapp.html", media_type="text/html")


async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


def create_app(
    settings: Settings | None = None,
    engine: BotEngine | None = None,
    balance_service: BalanceService | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.log_level)
        log_duration_settings(settings)
        if settings.app_env != "test":
            await warmup_engine()
        bot_engine = engine or create_engine(settings)
        await bot_engine.startup()
        app.state.bot_engine = bot_engine
        try:
            yield
        finally:
            await bot_engine.shutdown()
            await dispose_engine()

    app = FastAPI(
        title="TroMate Backend",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.balance_service = balance_service or BalanceService()
    app.include_router(health.router)
    app.include_router(mini_app.router, prefix="/api/miniapp")
    app.include_router(create_webhook_router(settings))
    app.add_api_route("/miniapp", miniapp_page, methods=["GET"], include_in_schema=False)
    app.add_api_route("/", root, methods=["GET"], include_in_schema=False)
    return app


app = create_app()
