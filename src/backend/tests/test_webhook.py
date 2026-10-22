from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_valid_webhook_update(client, fake_engine, webhook_headers) -> None:
    payload = {"update_id": 42, "message": {"message_id": 1}}
    response = await client.post("/webhook/telegram", json=payload, headers=webhook_headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake_engine.updates == [payload]


@pytest.mark.asyncio
async def test_missing_secret_is_rejected(client) -> None:
    response = await client.post(
        "/webhook/telegram",
        json={"update_id": 1},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_wrong_secret_is_rejected(client) -> None:
    response = await client.post(
        "/webhook/telegram",
        json={"update_id": 1},
        headers={
            "Content-Type": "application/json",
            "X-Telegram-Bot-Api-Secret-Token": "wrong-secret",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_wrong_content_type_is_rejected(client, webhook_headers) -> None:
    headers = dict(webhook_headers)
    headers["Content-Type"] = "text/plain"
    response = await client.post("/webhook/telegram", content=b"{}", headers=headers)
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_malformed_json_is_rejected(client, webhook_headers) -> None:
    response = await client.post(
        "/webhook/telegram",
        content=b"{",
        headers=webhook_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_non_object_json_is_rejected(client, webhook_headers) -> None:
    response = await client.post(
        "/webhook/telegram",
        content=b"[]",
        headers=webhook_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_oversized_body_is_rejected(client, webhook_headers) -> None:
    response = await client.post(
        "/webhook/telegram",
        content=b"x" * 1_048_577,
        headers=webhook_headers,
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_handler_exception_is_logged_and_acknowledged(
    client,
    fake_engine,
    webhook_headers,
    monkeypatch,
) -> None:
    async def broken_handler(payload):
        raise RuntimeError("handler exploded")

    monkeypatch.setattr(fake_engine, "handle_update", broken_handler)
    response = await client.post(
        "/webhook/telegram",
        json={"update_id": 7},
        headers=webhook_headers,
    )
    assert response.status_code == 200
