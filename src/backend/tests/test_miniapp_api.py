from __future__ import annotations

import json
import time

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
