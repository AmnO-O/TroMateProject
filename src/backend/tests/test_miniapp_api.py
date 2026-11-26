from __future__ import annotations

import json
import time
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

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


@pytest.mark.asyncio
async def test_balance_with_valid_init_data(client, settings) -> None:
    raw = sign_fields(base_fields(), settings.telegram_bot_token)
    response = await client.get(
        "/api/miniapp/balance",
        headers={"X-Telegram-Init-Data": raw},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["currency"] == "VND"
    assert len(body["balances"]) == 3
    assert body["balances"][0]["name"] == "Nam"


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
