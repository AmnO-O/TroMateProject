from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    engine = getattr(request.app.state, "bot_engine", None)
    return {
        "status": "ok",
        "library": settings.bot_library,
        "version": request.app.version,
        "bot_username": getattr(engine, "username", None),
        "webhook_path": settings.telegram_webhook_path,
    }
