from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.ai_extraction import AIExtractionAdapter
from app.bots.common import balance_text
from app.db.enums import ApprovalDecision, ExpenseStatus, RejectionReason, SplitType
from app.services.balance_service import BalanceService
from app.services.errors import PermissionDeniedError
from app.services.expense_service import ExpenseEdit, ExpenseService
from app.services.room_service import RoomService
from tests.db.conftest import pytestmark  # noqa: F401
from tests.db.helpers import CHAT_ID, make_expense, make_room


async def test_unknown_room_has_no_balances(uow_factory) -> None:
    service = BalanceService(uow_factory)
    assert await service.get_room_balances(CHAT_ID) is None
    assert await service.list_expenses(CHAT_ID, telegram_user_id=1) is None


async def test_new_room_lists_every_member_at_zero(uow_factory) -> None:
    room = await make_room(uow_factory)
    summary = await BalanceService(uow_factory).get_room_balances(CHAT_ID)
    assert summary.room_id == room.room_id and summary.room_name == "P302"
    assert [(b.display_name, b.amount) for b in summary.balances] == [
        ("Hao", 0),
        ("Lan", 0),
        ("Minh", 0),
    ]
    assert summary.is_settled and summary.transfers == ()


async def test_balances_follow_uc05_confirmation_immediately(uow_factory) -> None:
    room = await make_room(uow_factory)
    expense = await make_expense(uow_factory, room, total=300_000)
    balances = BalanceService(uow_factory)
    expenses = ExpenseService(uow_factory=uow_factory)

    # Sharing records the creator's AGREE (BR01); make_expense inserts the row directly.
    async with uow_factory() as uow:
        await uow.expenses.upsert_approval(
            expense_id=expense.id,
            member_id=room.rep.member_id,
            decision=ApprovalDecision.AGREE,
            expense_version=1,
        )
        await uow.commit()

    # PENDING expenses are not in the ledger yet.
    assert (await balances.get_room_balances(CHAT_ID)).is_settled

    for telegram_user_id in (2, 3):  # Lan and Minh agree
        review = await expenses.review(
            expense_id=expense.id,
            version=1,
            action="agree",
            telegram_chat_id=CHAT_ID,
            telegram_user_id=telegram_user_id,
        )
    assert review.status == ExpenseStatus.CONFIRMED

    summary = await balances.get_room_balances(CHAT_ID, telegram_user_id=2)
    assert summary.viewer_member_id == room.lan.member_id
    assert [(b.display_name, b.amount) for b in summary.balances] == [
        ("Hao", 200_000),
        ("Lan", -100_000),
        ("Minh", -100_000),
    ]
    assert sum(b.amount for b in summary.balances) == 0
    assert [(t.from_name, t.to_name, t.amount) for t in summary.transfers] == [
        ("Lan", "Hao", 100_000),
        ("Minh", "Hao", 100_000),
    ]
    text = balance_text(summary)
    assert "• Hao: +200,000đ" in text and "• Lan → Hao: 100,000đ" in text


async def test_overdue_auto_confirm_is_reflected_after_resolve_room(uow_factory) -> None:
    room = await make_room(uow_factory)
    await make_expense(
        uow_factory, room, total=90_000, deadline=datetime.now(UTC) - timedelta(minutes=1)
    )
    balances = BalanceService(uow_factory)
    assert (await balances.get_room_balances(CHAT_ID)).is_settled

    await ExpenseService(uow_factory=uow_factory).resolve_room(CHAT_ID)

    summary = await balances.get_room_balances(CHAT_ID)
    assert {b.display_name: b.amount for b in summary.balances} == {
        "Hao": 60_000,
        "Lan": -30_000,
        "Minh": -30_000,
    }


async def test_non_member_cannot_read_room(uow_factory) -> None:
    await make_room(uow_factory)
    service = BalanceService(uow_factory)
    with pytest.raises(PermissionDeniedError):
        await service.get_room_balances(CHAT_ID, telegram_user_id=999)
    with pytest.raises(PermissionDeniedError):
        await service.list_expenses(CHAT_ID, telegram_user_id=999)


async def test_expense_history_shows_viewer_share_and_hides_drafts(uow_factory) -> None:
    room = await make_room(uow_factory)
    pending = await make_expense(uow_factory, room, total=300_000)
    await make_expense(uow_factory, room, total=60_000, status=ExpenseStatus.DRAFT)

    records = await BalanceService(uow_factory).list_expenses(CHAT_ID, telegram_user_id=2)
    assert [r.expense_id for r in records] == [pending.id]
    [record] = records
    assert record.status == ExpenseStatus.PENDING
    assert record.payer_name == "Hao" and record.category_name == "Groceries"
    assert record.viewer_share == 100_000 and record.total_amount == 300_000


async def test_e2e_uc01_text_to_uc05_dispute_edit_confirm_and_live_balances(uow_factory) -> None:
    room_service = RoomService(uow_factory)
    common = {"telegram_chat_id": CHAT_ID, "chat_title": "Phòng 203"}
    await room_service.register_member(**common, telegram_user_id=1, display_name="Minh")
    await room_service.register_member(**common, telegram_user_id=2, display_name="Lan")
    await room_service.register_member(**common, telegram_user_id=3, display_name="Huy")
    await room_service.register_member(**common, telegram_user_id=4, display_name="An")

    expenses = ExpenseService(
        uow_factory=uow_factory,
        extractor=AIExtractionAdapter(api_key=""),
    )
    balances = BalanceService(uow_factory)

    draft = await expenses.prepare_expense_draft(
        telegram_chat_id=CHAT_ID,
        chat_title="Phòng 203",
        telegram_user_id=3,
        sender_display_name="Huy",
        sender_username="huy",
        text="Mua đồ chợ 300k cho Lan, Minh và tôi",
    )
    assert draft is not None
    created = await expenses.share_expense_draft(draft)
    assert created.status == ExpenseStatus.PENDING
    assert created.review_deadline is None

    # UC01-TC02 / BR01: PENDING expense does not change balances
    assert (await balances.get_room_balances(CHAT_ID, telegram_user_id=3)).is_settled

    # UC05-AF02: Minh rejects -> DISPUTED, balances remain 0
    disputed = await expenses.review(
        expense_id=created.expense_id,
        version=created.version,
        action="reject",
        telegram_chat_id=CHAT_ID,
        telegram_user_id=1,
        reason=RejectionReason.WRONG_AMOUNT,
    )
    assert disputed.status == ExpenseStatus.DISPUTED
    assert (await balances.get_room_balances(CHAT_ID)).is_settled

    # UC05-AF03: Creator Huy edits to 330k -> PENDING (110k each for Huy, Lan, Minh)
    edited = await expenses.review(
        expense_id=created.expense_id,
        version=disputed.version,
        action="edit",
        telegram_chat_id=CHAT_ID,
        telegram_user_id=3,
        edit=ExpenseEdit(
            description="Mua đồ chợ",
            total_amount=330_000,
            category_id=disputed.category_id,
            payer_id=disputed.payer_id,
            shares=dict.fromkeys(disputed.shares, 1),
            split_type=SplitType.EQUAL,
        ),
    )
    assert edited.status == ExpenseStatus.PENDING
    assert edited.agreed_count == 1

    # Lan agrees -> still PENDING; Minh agrees -> CONFIRMED + live balances updated
    after_lan = await expenses.review(
        expense_id=created.expense_id,
        version=edited.version,
        action="agree",
        telegram_chat_id=CHAT_ID,
        telegram_user_id=2,
    )
    assert after_lan.status == ExpenseStatus.PENDING
    assert (await balances.get_room_balances(CHAT_ID)).is_settled

    confirmed = await expenses.review(
        expense_id=created.expense_id,
        version=after_lan.version,
        action="agree",
        telegram_chat_id=CHAT_ID,
        telegram_user_id=1,
    )
    assert confirmed.status == ExpenseStatus.CONFIRMED

    summary = await balances.get_room_balances(CHAT_ID, telegram_user_id=3)
    assert {b.display_name: b.amount for b in summary.balances} == {
        "Minh": -110_000,
        "Lan": -110_000,
        "Huy": 220_000,
        "An": 0,
    }
    assert {(t.from_name, t.to_name, t.amount) for t in summary.transfers} == {
        ("Lan", "Huy", 110_000),
        ("Minh", "Huy", 110_000),
    }
