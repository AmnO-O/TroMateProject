"""PA4 end-to-end PostgreSQL integration test: UC01 -> UC03b -> UC05 -> live balances."""

from __future__ import annotations

from app.adapters.ai_extraction import AIExtractionAdapter
from app.db.enums import ExpenseStatus, RejectionReason, SplitType
from app.services.balance_service import BalanceService
from app.services.expense_service import ExpenseEdit, ExpenseService
from app.services.room_service import RoomService
from tests.db.conftest import pytestmark  # noqa: F401
from tests.db.helpers import CHAT_ID


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
