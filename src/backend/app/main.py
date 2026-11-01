from __future__ import annotations

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

WEB_DIR = Path(__file__).resolve().parent / "web"


async def miniapp_page() -> FileResponse:
    return FileResponse(WEB_DIR / "miniapp.html", media_type="text/html")


async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


def create_app(
    settings: Settings | None = None,
    engine: BotEngine | None = None,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.log_level)
        bot_engine = engine or create_engine(settings)
        await bot_engine.startup()
        app.state.bot_engine = bot_engine
        try:
            yield
        finally:
            await bot_engine.shutdown()

    app = FastAPI(
        title="TroMate Backend",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(health.router)
    app.include_router(mini_app.router, prefix="/api/miniapp")
    app.include_router(create_webhook_router(settings))
    app.add_api_route("/miniapp", miniapp_page, methods=["GET"], include_in_schema=False)
    app.add_api_route("/", root, methods=["GET"], include_in_schema=False)
    return app


app = create_app()
