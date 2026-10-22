from __future__ import annotations

import json
import logging
import secrets
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config import Settings

logger = logging.getLogger(__name__)


def create_router(settings: Settings) -> APIRouter:
    router = APIRouter()

    @router.post(settings.telegram_webhook_path, include_in_schema=False)
    async def telegram_webhook(request: Request) -> dict[str, bool]:
        provided_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not provided_secret or not secrets.compare_digest(
            provided_secret,
            settings.telegram_webhook_secret,
        ):
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

        content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type != "application/json":
            raise HTTPException(status_code=415, detail="Expected application/json")

        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > settings.miniapp_max_body_bytes:
                raise HTTPException(status_code=413, detail="Update is too large")

        body = await request.body()
        if len(body) > settings.miniapp_max_body_bytes:
            raise HTTPException(status_code=413, detail="Update is too large")

        try:
            payload: Any = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Malformed JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Update must be a JSON object")

        engine = getattr(request.app.state, "bot_engine", None)
        if engine is None:
            raise HTTPException(status_code=503, detail="Bot engine is not ready")

        update_id = payload.get("update_id")
        update_type = next((key for key in payload if key != "update_id"), "unknown")
        try:
            await engine.handle_update(payload)
        except Exception:
            logger.exception(
                "Failed to hand off Telegram update: update_id=%s type=%s",
                update_id,
                update_type,
            )
        logger.info(
            "Accepted Telegram update: update_id=%s type=%s",
            update_id,
            update_type,
        )
        return {"ok": True}

    return router
