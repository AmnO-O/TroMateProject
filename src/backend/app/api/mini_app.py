from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from app.core.init_data import InitDataError, ValidatedInitData, validate_init_data
from app.core.sample_data import MOCK_BALANCES
from app.db.enums import RejectionReason, SplitType
from app.services.errors import ServiceError
from app.services.expense_service import ExpenseEdit

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


async def _resolve_chat(session, request):
    engine = request.app.state.bot_engine
    if session.chat and session.user and hasattr(engine, "resolve_room"):
        try:
            await engine.resolve_room(session.chat["id"], user_id=session.user["id"])
        except ServiceError as exc:
            raise HTTPException(exc.http_status, exc.message) from exc


@router.post("/session")
async def create_session(payload: SessionRequest, request: Request) -> dict[str, Any]:
    validated = _validate(payload.init_data, request)
    await _resolve_chat(validated, request)
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
    await _resolve_chat(validated, request)
    return {
        "ok": True,
        "user": validated.user,
        "currency": "VND",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "balances": MOCK_BALANCES,
    }


class EditFields(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    total_amount: int = Field(gt=0, le=9_007_199_254_740_991)
    category_id: UUID
    payer_id: UUID
    shares: dict[UUID, int]
    split_type: Literal["EQUAL", "CUSTOM_AMOUNT", "CUSTOM_RATIO"]


class ReviewRequest(BaseModel):
    action: Literal["refresh", "edit", "reject", "addreason", "cancel", "agree"]
    version: int = Field(ge=1)
    edit: EditFields | None = None
    reason: RejectionReason | None = None
    note: str | None = Field(default=None, max_length=300)


@router.post("/expense")
async def review_expense(
    payload: ReviewRequest, request: Request, init_data: str = Header(alias="X-Telegram-Init-Data")
):
    session = _validate(init_data, request)
    try:
        prefix, raw_id, raw_chat, link_version, intent = (session.start_param or "").split("_")
        if prefix != "expense" or not session.user:
            raise ValueError
        expense_id, chat_id, user_id = UUID(raw_id), int(raw_chat), int(session.user["id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(400, "Liên kết khoản chi không hợp lệ.") from exc
    if payload.action != "refresh" and (
        str(payload.version) != link_version or payload.action != intent
    ):
        raise HTTPException(409, "Hãy mở đúng thao tác trên thẻ mới nhất.")
    engine = request.app.state.bot_engine
    if not hasattr(engine, "expense_service"):
        raise HTTPException(503, "Bot xử lý khoản chi chưa sẵn sàng.")
    fields = None
    if payload.edit:
        fields = ExpenseEdit(
            **payload.edit.model_dump(exclude={"split_type"}),
            split_type=SplitType(payload.edit.split_type),
        )
    try:
        service = engine.expense_service
        review_args = dict(
            expense_id=expense_id,
            telegram_chat_id=chat_id,
            telegram_user_id=user_id,
            version=payload.version,
        )
        await engine.resolve_room(chat_id, user_id=user_id)
        before = await service.review(**review_args, action="refresh")
        if payload.action == "refresh":
            return jsonable_encoder(before, exclude={"mentions"})
        result = await service.review(
            **review_args,
            action=payload.action,
            edit=fields,
            reason=payload.reason if payload.action in {"reject", "addreason"} else None,
            note=payload.note if payload.action in {"reject", "addreason"} else None,
        )
        engine.wake_delivery()
        return jsonable_encoder(result, exclude={"mentions"})
    except ServiceError as exc:
        raise HTTPException(exc.http_status, exc.message) from exc
