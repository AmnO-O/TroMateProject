from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.bots.common import (
    BALANCE_PRIVATE_CHAT_TEXT,
    BALANCE_UNAVAILABLE_TEXT,
    balance_text,
    live_balance_text,
    miniapp_direct_link,
)
from app.services.balance_service import MemberBalance, RoomBalances, SuggestedTransfer

HAO, LAN = uuid.uuid4(), uuid.uuid4()


def make_summary(hao: int = 100_000, lan: int = -100_000) -> RoomBalances:
    transfers = (SuggestedTransfer(LAN, "Lan", HAO, "Hao", hao),) if hao else ()
    return RoomBalances(
        room_id=uuid.uuid4(),
        room_name="P302",
        telegram_chat_id=-100,
        balances=(MemberBalance(HAO, 1, "Hao", hao), MemberBalance(LAN, 2, "Lan", lan)),
        transfers=transfers,
        viewer_member_id=None,
        generated_at=datetime(2026, 11, 26, 3, 0, tzinfo=UTC),
    )


def test_balance_text_lists_members_and_suggested_transfers() -> None:
    text = balance_text(make_summary())
    assert "Số dư phòng P302" in text
    assert "• Hao: +100,000đ (được nhận)" in text
    assert "• Lan: -100,000đ (cần trả)" in text
    assert "• Lan → Hao: 100,000đ" in text
    assert "26/11/2026 10:00:00 (GMT+7)" in text
    assert "mock" not in text.lower()


def test_balance_text_when_everyone_is_even() -> None:
    text = balance_text(make_summary(0, 0))
    assert "không ai nợ ai" in text
    assert "Gợi ý thanh toán" not in text


def test_balance_text_for_unknown_room_points_to_new() -> None:
    assert "/new" in balance_text(None)


@pytest.mark.asyncio
async def test_live_balance_text_reads_the_group_room() -> None:
    service = AsyncMock()
    service.get_room_balances.return_value = make_summary()
    text = await live_balance_text(service, -100, "supergroup")
    service.get_room_balances.assert_awaited_once_with(-100)
    assert "P302" in text


@pytest.mark.asyncio
async def test_live_balance_text_in_private_chat_does_not_query() -> None:
    service = AsyncMock()
    assert await live_balance_text(service, 42, "private") == BALANCE_PRIVATE_CHAT_TEXT
    service.get_room_balances.assert_not_awaited()


@pytest.mark.asyncio
async def test_live_balance_text_hides_database_errors() -> None:
    service = AsyncMock()
    service.get_room_balances.side_effect = RuntimeError("db down")
    assert await live_balance_text(service, -100, "group") == BALANCE_UNAVAILABLE_TEXT


def test_room_link_carries_the_group_chat() -> None:
    assert (
        miniapp_direct_link("tromate_bot", -1001) == "https://t.me/tromate_bot?startapp=room_-1001"
    )
    assert miniapp_direct_link("tromate_bot") == "https://t.me/tromate_bot?startapp=group"
