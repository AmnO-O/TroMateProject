from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from app.core.init_data import InitDataError, ValidatedInitData, validate_init_data
from app.db.enums import RejectionReason, SplitType
from app.services.balance_service import (
    DEFAULT_EXPENSE_LIMIT,
    MAX_EXPENSE_LIMIT,
    BalanceService,
    RoomBalances,
)
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


def _require_init_data(init_data: str | None) -> str:
    if not init_data:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "MISSING_INIT_DATA",
                "message": "X-Telegram-Init-Data header is required",
            },
        )
    return init_data


def _service_http_error(exc: ServiceError) -> HTTPException:
    return HTTPException(exc.http_status, {"code": exc.code, "message": exc.message})


async def _sync_room(request: Request, chat_id: int, user_id: int) -> None:
    """Apply due auto-confirmations so balances include them (no-op without a bot engine)."""

    engine = request.app.state.bot_engine
    if hasattr(engine, "resolve_room"):
        try:
            await engine.resolve_room(chat_id, user_id=user_id)
        except ServiceError as exc:
            raise _service_http_error(exc) from exc


async def _resolve_chat(session, request):
    if session.chat and session.user:
        await _sync_room(request, int(session.chat["id"]), int(session.user["id"]))


def _room_chat_id(session: ValidatedInitData) -> int | None:
    """Telegram chat of the room the Mini App was opened for, if the launch names one.

    ``chat`` is only sent for attachment-menu launches; direct links carry the chat in
    ``start_param`` instead (``room_<chat_id>`` from /balance and /app, or an expense link).
    Anyone can craft a ``start_param``, so callers must still check room membership.
    """

    if session.chat and "id" in session.chat:
        return int(session.chat["id"])
    param = session.start_param or ""
    try:
        if param.startswith("room_"):
            return int(param.removeprefix("room_"))
        if param.startswith("expense_"):
            return int(param.split("_")[2])
    except (IndexError, ValueError):
        return None
    return None


async def _room_context(
    init_data: str | None, request: Request
) -> tuple[ValidatedInitData, int, int | None]:
    session = _validate(_require_init_data(init_data), request)
    if not session.user or "id" not in session.user:
        raise HTTPException(
            400, {"code": "MISSING_USER", "message": "initData does not identify a user"}
        )
    user_id = int(session.user["id"])
    chat_id = _room_chat_id(session)
    if chat_id is not None:
        await _sync_room(request, chat_id, user_id)
    return session, user_id, chat_id


def _balance_service(request: Request) -> BalanceService:
    return request.app.state.balance_service


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _balances_payload(summary: RoomBalances) -> dict[str, Any]:
    return {
        "room": {"id": str(summary.room_id), "name": summary.room_name},
        "settled": summary.is_settled,
        "balances": [
            {
                "member_id": str(item.member_id),
                "telegram_user_id": item.telegram_user_id,
                "name": item.display_name,
                "amount": item.amount,
                "is_me": item.member_id == summary.viewer_member_id,
            }
            for item in summary.balances
        ],
        "transfers": [
            {
                "from_member_id": str(t.from_member_id),
                "from_name": t.from_name,
                "to_member_id": str(t.to_member_id),
                "to_name": t.to_name,
                "amount": t.amount,
            }
            for t in summary.transfers
        ],
    }


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
    """Live net balances of the room, computed from confirmed ledger entries."""

    session, user_id, chat_id = await _room_context(init_data, request)
    summary = None
    if chat_id is not None:
        try:
            summary = await _balance_service(request).get_room_balances(
                chat_id, telegram_user_id=user_id
            )
        except ServiceError as exc:
            raise _service_http_error(exc) from exc
    body: dict[str, Any] = {
        "ok": True,
        "user": session.user,
        "currency": "VND",
        "generated_at": _now_iso(),
    }
    if summary is None:
        # Opened outside a group (or the group has never used the bot): nothing to show yet.
        return body | {"room": None, "settled": True, "balances": [], "transfers": []}
    return body | _balances_payload(summary)


@router.get("/expenses")
async def list_expenses(
    request: Request,
    init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
    limit: int = Query(default=DEFAULT_EXPENSE_LIMIT, ge=1, le=MAX_EXPENSE_LIMIT),
) -> dict[str, Any]:
    """Newest shared expenses of the room with the caller's own share of each."""

    _, user_id, chat_id = await _room_context(init_data, request)
    records = None
    if chat_id is not None:
        try:
            records = await _balance_service(request).list_expenses(
                chat_id, telegram_user_id=user_id, limit=limit
            )
        except ServiceError as exc:
            raise _service_http_error(exc) from exc
    return {
        "ok": True,
        "currency": "VND",
        "generated_at": _now_iso(),
        "expenses": [
            {
                "id": str(r.expense_id),
                "description": r.description,
                "total_amount": r.total_amount,
                "payer_name": r.payer_name,
                "category_name": r.category_name,
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
                "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
                "my_share": r.viewer_share,
            }
            for r in records or ()
        ],
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
