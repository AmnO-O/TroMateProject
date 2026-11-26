from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.db.enums import ExpenseStatus
from app.services.balance_service import (
    ExpenseRecord,
    MemberBalance,
    RoomBalances,
    SuggestedTransfer,
)
from app.services.errors import PermissionDeniedError
from tests.helpers import base_fields, replace_fields, sign_fields


@pytest.mark.asyncio
async def test_health(client, settings) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["library"] == settings.bot_library
    assert body["bot_username"] == "fake_bot"


@pytest.mark.asyncio
async def test_valid_session(client, settings) -> None:
    now = int(time.time())
    raw = sign_fields(base_fields(now), settings.telegram_bot_token)
    response = await client.post("/api/miniapp/session", json={"init_data": raw})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["user"]["id"] == 123456789
    assert body["chat_type"] == "supergroup"
    assert body["start_param"] == "group"


@pytest.mark.asyncio
async def test_tampered_session_is_rejected(client, settings) -> None:
    now = int(time.time())
    raw = sign_fields(base_fields(now), settings.telegram_bot_token)
    tampered_user = json.dumps(
        {"id": 999, "first_name": "Mallory", "username": "mallory"},
        separators=(",", ":"),
    )
    response = await client.post(
        "/api/miniapp/session",
        json={"init_data": replace_fields(raw, user=tampered_user)},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
async def test_empty_session_is_rejected(client) -> None:
    response = await client.post("/api/miniapp/session", json={"init_data": ""})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_INIT_DATA"


@pytest.mark.asyncio
async def test_missing_session_field_is_validation_error(client) -> None:
    response = await client.post("/api/miniapp/session", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_expired_session_is_rejected(client, settings) -> None:
    now = int(time.time())
    raw = sign_fields(base_fields(now - 7200), settings.telegram_bot_token)
    response = await client.post("/api/miniapp/session", json={"init_data": raw})
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "EXPIRED_INIT_DATA"


def _room_balances(viewer_id: uuid.UUID) -> RoomBalances:
    other = uuid.uuid4()
    return RoomBalances(
        room_id=uuid.uuid4(),
        room_name="P302",
        telegram_chat_id=-100,
        balances=(
            MemberBalance(other, 1, "Hao", 150_000),
            MemberBalance(viewer_id, 123456789, "Nam", -150_000),
        ),
        transfers=(SuggestedTransfer(viewer_id, "Nam", other, "Hao", 150_000),),
        viewer_member_id=viewer_id,
        generated_at=datetime.now(UTC),
    )


@pytest.fixture
def balance_service(app) -> AsyncMock:
    service = AsyncMock()
    app.state.balance_service = service
    return service


@pytest.mark.asyncio
async def test_balance_returns_live_room_balances(
    client, settings, fake_engine, balance_service
) -> None:
    viewer = uuid.uuid4()
    balance_service.get_room_balances.return_value = _room_balances(viewer)
    fake_engine.resolve_room = AsyncMock()
    raw = sign_fields(base_fields(start_param="room_-100"), settings.telegram_bot_token)
    response = await client.get("/api/miniapp/balance", headers={"X-Telegram-Init-Data": raw})

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True and body["currency"] == "VND"
    assert body["room"]["name"] == "P302" and body["settled"] is False
    assert [(b["name"], b["amount"], b["is_me"]) for b in body["balances"]] == [
        ("Hao", 150_000, False),
        ("Nam", -150_000, True),
    ]
    assert body["transfers"] == [
        {
            "from_member_id": str(viewer),
            "from_name": "Nam",
            "to_member_id": body["balances"][0]["member_id"],
            "to_name": "Hao",
            "amount": 150_000,
        }
    ]
    # Due auto-confirmations run first, then the authenticated member's room is read.
    fake_engine.resolve_room.assert_awaited_once_with(-100, user_id=123456789)
    balance_service.get_room_balances.assert_awaited_once_with(-100, telegram_user_id=123456789)


@pytest.mark.asyncio
async def test_balance_uses_chat_from_expense_link(client, settings, balance_service) -> None:
    balance_service.get_room_balances.return_value = None
    fields = base_fields(start_param=f"expense_{uuid.uuid4().hex}_-200_1_edit")
    raw = sign_fields(fields, settings.telegram_bot_token)
    response = await client.get("/api/miniapp/balance", headers={"X-Telegram-Init-Data": raw})
    assert response.status_code == 200 and response.json()["room"] is None
    balance_service.get_room_balances.assert_awaited_once_with(-200, telegram_user_id=123456789)


@pytest.mark.asyncio
@pytest.mark.parametrize("start_param", ["group", "room_not-a-chat", ""])
async def test_balance_without_room_context_is_empty(
    client, settings, balance_service, start_param
) -> None:
    raw = sign_fields(base_fields(start_param=start_param), settings.telegram_bot_token)
    response = await client.get("/api/miniapp/balance", headers={"X-Telegram-Init-Data": raw})
    assert response.status_code == 200
    body = response.json()
    assert body["room"] is None and body["balances"] == [] and body["transfers"] == []
    balance_service.get_room_balances.assert_not_awaited()


@pytest.mark.asyncio
async def test_balance_of_a_room_the_user_is_not_in_is_forbidden(
    client, settings, balance_service
) -> None:
    balance_service.get_room_balances.side_effect = PermissionDeniedError(
        "Bạn không thuộc phòng này."
    )
    raw = sign_fields(base_fields(start_param="room_-100"), settings.telegram_bot_token)
    response = await client.get("/api/miniapp/balance", headers={"X-Telegram-Init-Data": raw})
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_expenses_returns_room_records(client, settings, balance_service) -> None:
    expense_id = uuid.uuid4()
    created = datetime(2026, 11, 26, 3, 0, tzinfo=UTC)
    balance_service.list_expenses.return_value = (
        ExpenseRecord(
            expense_id=expense_id,
            description="Đi chợ",
            total_amount=300_000,
            payer_name="Hao",
            category_name="Groceries",
            status=ExpenseStatus.CONFIRMED,
            created_at=created,
            confirmed_at=created,
            viewer_share=100_000,
        ),
    )
    raw = sign_fields(base_fields(start_param="room_-100"), settings.telegram_bot_token)
    response = await client.get(
        "/api/miniapp/expenses?limit=5", headers={"X-Telegram-Init-Data": raw}
    )
    assert response.status_code == 200
    [record] = response.json()["expenses"]
    assert record["id"] == str(expense_id) and record["status"] == "CONFIRMED"
    assert record["my_share"] == 100_000 and record["payer_name"] == "Hao"
    balance_service.list_expenses.assert_awaited_once_with(
        -100, telegram_user_id=123456789, limit=5
    )


@pytest.mark.asyncio
async def test_expenses_requires_init_data(client) -> None:
    response = await client.get("/api/miniapp/expenses")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "MISSING_INIT_DATA"


@pytest.mark.asyncio
async def test_balance_without_init_data_is_rejected(client) -> None:
    response = await client.get("/api/miniapp/balance")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "MISSING_INIT_DATA"


@pytest.mark.asyncio
async def test_balance_with_invalid_init_data_is_rejected(client, settings) -> None:
    raw = sign_fields(base_fields(), "999:OTHER_TOKEN")
    response = await client.get(
        "/api/miniapp/balance",
        headers={"X-Telegram-Init-Data": raw},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
async def test_miniapp_page_is_served(client) -> None:
    response = await client.get("/miniapp")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "TroMate Mini App" in response.text


@pytest.mark.asyncio
async def test_expense_link_checks_signature_intent_and_version(client, settings):
    fields = base_fields()
    fields["start_param"] = "expense_12345678123456781234567812345678_-100_3_edit"
    path = "/api/miniapp/expense"
    raw = sign_fields(fields, settings.telegram_bot_token)
    for action, version in [("cancel", 3), ("edit", 2)]:
        response = await client.post(
            path, headers={"X-Telegram-Init-Data": raw}, json={"action": action, "version": version}
        )
        assert response.status_code == 409
    response = await client.post(
        path,
        headers={"X-Telegram-Init-Data": sign_fields(fields, "other")},
        json={"action": "refresh", "version": 3},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_dispute_uses_authenticated_member(client, settings, fake_engine):
    expense_id = uuid.uuid4()
    fields = base_fields(start_param=f"expense_{expense_id.hex}_-100_2_reject")
    fake_engine.resolve_room = AsyncMock()
    fake_engine.expense_service = SimpleNamespace(
        review=AsyncMock(side_effect=[{"status": "PENDING"}, {"status": "DISPUTED"}])
    )
    fake_engine.wake_delivery = Mock()
    response = await client.post(
        "/api/miniapp/expense",
        headers={"X-Telegram-Init-Data": sign_fields(fields, settings.telegram_bot_token)},
        json={"action": "reject", "version": 2, "reason": "OTHER", "note": "Sai kỳ"},
    )
    assert response.status_code == 200 and response.json()["status"] == "DISPUTED"
    kwargs = fake_engine.expense_service.review.await_args.kwargs
    assert kwargs["telegram_user_id"] == 123456789 and kwargs["expense_id"] == expense_id
    assert kwargs["reason"] == "OTHER" and kwargs["note"] == "Sai kỳ"
    fake_engine.wake_delivery.assert_called_once_with()
