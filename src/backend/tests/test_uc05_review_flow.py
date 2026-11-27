"""Non-DB unit and Mini App API tests for UC05 review, dispute, edit, and cancel flows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.bots.expense_card import build_confirmation_keyboard, render_confirmation_card_html
from app.bots.interface import ConfirmationCardDTO, SplitLineDTO
from app.db.enums import ApprovalDecision, ExpenseStatus, RejectionReason, SplitType
from app.services.expense_service import ExpenseReview
from tests.helpers import base_fields, sign_fields


def _make_card(
    *,
    status: str = "PENDING",
    review_deadline: datetime | None = None,
    rejection: str | None = None,
    balances: tuple[tuple[str, int], ...] = (),
) -> ConfirmationCardDTO:
    return ConfirmationCardDTO(
        expense_id=uuid.UUID("00000000-0000-0000-0000-000000000101"),
        version=2,
        description="Mua đồ chợ",
        total_amount=300_000,
        payer_name="Huy",
        category_name="Groceries",
        status=status,  # type: ignore[arg-type]
        splits=(
            SplitLineDTO("Huy", 100_000, "AGREE"),
            SplitLineDTO("Lan", 100_000, "PENDING"),
            SplitLineDTO("Minh", 100_000, "REJECT" if status == "DISPUTED" else "PENDING"),
        ),
        review_deadline=review_deadline,
        miniapp_edit_url="https://t.me/fake_bot?startapp=expense_123_-100_2",
        agreed_count=3 if status == "CONFIRMED" else 1,
        voter_count=3,
        payer_decision="AGREE",
        split_method="EQUAL",
        balances=balances,
        rejection=rejection,
    )


def _button_labels(card: ConfirmationCardDTO) -> list[str]:
    markup = build_confirmation_keyboard(card)
    return [btn.text for row in markup.inline_keyboard for btn in row]


def test_confirmation_card_rendering_for_uc05_states() -> None:
    pending_auto = _make_card(
        status="PENDING",
        review_deadline=datetime(2026, 11, 27, 10, 0, tzinfo=UTC),
    )
    html_auto = render_confirmation_card_html(pending_auto)
    assert "Chờ xác nhận" in html_auto
    assert "Hạn xác nhận:" in html_auto
    assert _button_labels(pending_auto) == [
        "✓ Đồng ý",
        "✕ Từ chối",
        "✎ Chỉnh sửa",
        "Hủy khoản chi",
    ]

    pending_manual = _make_card(status="PENDING", review_deadline=None)
    html_manual = render_confirmation_card_html(pending_manual)
    assert "Duyệt thủ công — BR02" in html_manual
    assert "Không tự động xác nhận" in html_manual

    disputed = _make_card(status="DISPUTED", rejection="Minh: Sai số tiền")
    html_disputed = render_confirmation_card_html(disputed)
    assert "Đã từ chối" in html_disputed
    assert "Lý do từ chối: Minh: Sai số tiền" in html_disputed
    assert _button_labels(disputed) == ["Thêm lý do", "✎ Chỉnh sửa", "Hủy khoản chi"]

    confirmed = _make_card(
        status="CONFIRMED",
        balances=(("Huy", 200_000), ("Lan", -100_000), ("Minh", -100_000)),
    )
    html_confirmed = render_confirmation_card_html(confirmed)
    assert "Đã xác nhận" in html_confirmed
    assert "Số dư sau xác nhận:" in html_confirmed
    assert "Huy: +200,000đ" in html_confirmed

    cancelled = _make_card(status="CANCELLED")
    assert "Đã hủy" in render_confirmation_card_html(cancelled)


def _sample_review(expense_id: uuid.UUID, *, status: ExpenseStatus, version: int) -> ExpenseReview:
    cat_id = uuid.UUID("00000000-0000-0000-0000-000000000201")
    huy_id = uuid.UUID("00000000-0000-0000-0000-000000000301")
    lan_id = uuid.UUID("00000000-0000-0000-0000-000000000302")
    return ExpenseReview(
        content_revision=1,
        expense_id=expense_id,
        version=version,
        description="Mua đồ chợ",
        total_amount=300_000,
        payer_name="Huy",
        category_name="Groceries",
        status=status,
        splits=(),
        review_deadline=None,
        agreed_count=1,
        voter_count=2,
        category_id=cat_id,
        payer_id=huy_id,
        shares={huy_id: 150_000, lan_id: 150_000},
        ratios={},
        mentions=((123456789, "Huy"),),
        members={huy_id: "Huy", lan_id: "Lan"},
        categories={cat_id: "Groceries"},
        can_edit=True,
        can_cancel=True,
        last_change="",
        can_add_reason=False,
        can_vote=False,
        split_type=SplitType.EQUAL,
        balances=(),
        rejection=None,
        payer_decision=ApprovalDecision.AGREE,
    )


async def test_miniapp_expense_review_actions_and_guards(client, settings, fake_engine) -> None:
    expense_id = uuid.UUID("00000000-0000-0000-0000-000000000401")
    cat_id = uuid.UUID("00000000-0000-0000-0000-000000000201")
    huy_id = uuid.UUID("00000000-0000-0000-0000-000000000301")
    lan_id = uuid.UUID("00000000-0000-0000-0000-000000000302")

    # Engine without expense_service returns 503
    init_refresh = sign_fields(
        base_fields(start_param=f"expense_{expense_id.hex}_-100123_1_edit"),
        settings.telegram_bot_token,
    )
    unavailable = await client.post(
        "/api/miniapp/expense",
        headers={"X-Telegram-Init-Data": init_refresh},
        json={"action": "refresh", "version": 1},
    )
    assert unavailable.status_code == 503

    # Attach mocked UC05 service hooks to fake_engine
    review_mock = AsyncMock(
        side_effect=[
            _sample_review(expense_id, status=ExpenseStatus.PENDING, version=1),
            _sample_review(expense_id, status=ExpenseStatus.PENDING, version=1),
            _sample_review(expense_id, status=ExpenseStatus.PENDING, version=2),
            _sample_review(expense_id, status=ExpenseStatus.DISPUTED, version=2),
            _sample_review(expense_id, status=ExpenseStatus.DISPUTED, version=3),
            _sample_review(expense_id, status=ExpenseStatus.DISPUTED, version=3),
            _sample_review(expense_id, status=ExpenseStatus.CANCELLED, version=4),
        ]
    )
    fake_engine.expense_service = SimpleNamespace(review=review_mock)
    fake_engine.resolve_room = AsyncMock()
    fake_engine.wake_delivery = Mock()

    # 1. refresh succeeds and strips internal mentions field
    res_refresh = await client.post(
        "/api/miniapp/expense",
        headers={"X-Telegram-Init-Data": init_refresh},
        json={"action": "refresh", "version": 1},
    )
    assert res_refresh.status_code == 200
    assert "mentions" not in res_refresh.json()
    fake_engine.wake_delivery.assert_not_called()

    # 2. Stale version or intent mismatch returns 409 (UC05-AF08)
    stale = await client.post(
        "/api/miniapp/expense",
        headers={"X-Telegram-Init-Data": init_refresh},
        json={"action": "edit", "version": 99},
    )
    assert stale.status_code == 409

    wrong_intent = await client.post(
        "/api/miniapp/expense",
        headers={"X-Telegram-Init-Data": init_refresh},
        json={"action": "cancel", "version": 1},
    )
    assert wrong_intent.status_code == 409

    # 3. edit with CUSTOM_RATIO forwards ExpenseEdit and wakes delivery
    res_edit = await client.post(
        "/api/miniapp/expense",
        headers={"X-Telegram-Init-Data": init_refresh},
        json={
            "action": "edit",
            "version": 1,
            "edit": {
                "description": "Mua đồ chợ",
                "total_amount": 300_000,
                "category_id": str(cat_id),
                "payer_id": str(huy_id),
                "shares": {str(huy_id): 6000, str(lan_id): 4000},
                "split_type": "CUSTOM_RATIO",
            },
        },
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["version"] == 2
    edit_call = review_mock.await_args_list[2].kwargs
    assert edit_call["action"] == "edit"
    assert edit_call["edit"].split_type == SplitType.CUSTOM_RATIO

    # 4. reject with OTHER note forwards reason and note
    init_reject = sign_fields(
        base_fields(start_param=f"expense_{expense_id.hex}_-100123_2_reject"),
        settings.telegram_bot_token,
    )
    res_reject = await client.post(
        "/api/miniapp/expense",
        headers={"X-Telegram-Init-Data": init_reject},
        json={
            "action": "reject",
            "version": 2,
            "reason": "OTHER",
            "note": "Tôi chỉ lấy 50k",
        },
    )
    assert res_reject.status_code == 200
    reject_call = review_mock.await_args_list[4].kwargs
    assert reject_call["reason"] == RejectionReason.OTHER
    assert reject_call["note"] == "Tôi chỉ lấy 50k"

    # 5. cancel succeeds and wakes delivery
    init_cancel = sign_fields(
        base_fields(start_param=f"expense_{expense_id.hex}_-100123_3_cancel"),
        settings.telegram_bot_token,
    )
    res_cancel = await client.post(
        "/api/miniapp/expense",
        headers={"X-Telegram-Init-Data": init_cancel},
        json={"action": "cancel", "version": 3},
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"
    assert fake_engine.wake_delivery.call_count == 3
