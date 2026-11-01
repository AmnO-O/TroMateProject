from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.core.init_data import InitDataError, ValidatedInitData, validate_init_data
from app.core.sample_data import MOCK_BALANCES

router = APIRouter()


class SessionRequest(BaseModel):
    init_data: str


def _validate(raw_init_data: str, request: Request) -> ValidatedInitData:
    settings = request.app.state.settings
    try:
        return validate_init_data(
            raw_init_data,
            settings.telegram_bot_token,
            max_age_seconds=settings.miniapp_initdata_max_age_seconds,
            max_length=settings.miniapp_initdata_max_length,
        )
    except InitDataError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.post("/session")
async def create_session(payload: SessionRequest, request: Request) -> dict[str, Any]:
    validated = _validate(payload.init_data, request)
    return {
        "ok": True,
        "user": validated.user,
        "auth_date": validated.auth_date,
        "query_id": validated.query_id,
        "chat": validated.chat,
        "chat_type": validated.chat_type,
        "chat_instance": validated.chat_instance,
        "start_param": validated.start_param,
    }


@router.get("/balance")
async def get_balance(
    request: Request,
    init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> dict[str, Any]:
    if not init_data:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "MISSING_INIT_DATA",
                "message": "X-Telegram-Init-Data header is required",
            },
        )
    validated = _validate(init_data, request)
    return {
        "ok": True,
        "user": validated.user,
        "currency": "VND",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "balances": MOCK_BALANCES,
    }
