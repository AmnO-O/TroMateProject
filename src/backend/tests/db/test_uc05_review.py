import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.db.enums import ApprovalDecision, RejectionReason, ReviewDefaultAction, SplitType
from app.db.models.expense_model import ExpenseDelivery
from app.repositories.room_repository import RoomRepository
from app.services.errors import ConflictError, PermissionDeniedError, ValidationError
from app.services.expense_service import ExpenseEdit, ExpenseService
from app.services.room_service import RoomService
from tests.db.conftest import pytestmark  # noqa: F401
from tests.db.helpers import CHAT_ID, make_expense, make_room


async def test_review_revision_and_ledger(uow_factory):
    room = await make_room(uow_factory)
    expense = await make_expense(uow_factory, room)
    service = ExpenseService(uow_factory=uow_factory)

    async def review(user, action, version, **kwargs):
        return await service.review(
            telegram_chat_id=CHAT_ID,
            telegram_user_id=user,
            expense_id=expense.id,
            action=action,
            version=version,
            **kwargs,
        )

    async def assert_approval_versions(expected_members):
        async with uow_factory() as uow:
            saved = await uow.expenses.get(expense.id)
            assert {a.member_id for a in saved.approvals} == expected_members
            assert all(a.expense_version == saved.version for a in saved.approvals)

    with pytest.raises(PermissionDeniedError):
        await review(4, "agree", 1)
    assert (await review(3, "agree", 1)).agreed_count == 1
    disputed = await review(2, "reject", 1, reason=RejectionReason.WRONG_AMOUNT)
    assert disputed.status == "DISPUTED"
    await assert_approval_versions({room.lan.member_id, room.minh.member_id})
    with pytest.raises(PermissionDeniedError):
        await review(2, "edit", disputed.version)
    revised = await review(
        1,
        "edit",
        disputed.version,
        edit=ExpenseEdit(
            "Updated groceries",
            expense.total_amount,
            expense.category_id,
            expense.payer_member_id,
            {s.member_id: s.share_amount for s in expense.splits},
            SplitType.EQUAL,
        ),
    )
    assert revised.description == "Updated groceries"
    assert revised.agreed_count == 1
    with pytest.raises(ConflictError):
        await review(3, "agree", 1)
    assert (await review(2, "agree", revised.version)).status == "PENDING"
    assert (await review(3, "agree", revised.version)).status == "CONFIRMED"
    await assert_approval_versions({room.rep.member_id, room.lan.member_id, room.minh.member_id})
    with pytest.raises(ConflictError):
        await review(3, "agree", revised.version)
    async with uow_factory() as uow:
        assert await uow.ledger.net_balances(room.room_id) == {
            room.rep.member_id: 200_000,
            room.lan.member_id: -100_000,
            room.minh.member_id: -100_000,
        }


async def test_share_edit_reject_cancel(uow_factory):
    room = await make_room(uow_factory)
    service = ExpenseService(uow_factory=uow_factory)
    draft = await service.prepare_expense_draft(
        telegram_chat_id=CHAT_ID,
        chat_title="P302",
        telegram_user_id=1,
        sender_display_name="Hao",
        sender_username=None,
        text="Lunch 100k chia Lan, Minh",
    )
    created = await service.share_expense_draft(draft)

    async def review(user, action, version, **kwargs):
        return await service.review(
            expense_id=created.expense_id,
            version=version,
            action=action,
            telegram_chat_id=CHAT_ID,
            telegram_user_id=user,
            **kwargs,
        )

    active = await review(1, "refresh", created.version)
    assert active.agreed_count == 1 and active.review_deadline is None
    category = next(k for k, v in active.categories.items() if v == "Utilities")
    with pytest.raises(PermissionDeniedError):
        await review(2, "edit", active.version)
    assert not (await review(2, "refresh", active.version)).can_edit
    updated = await review(
        1,
        "edit",
        active.version,
        edit=ExpenseEdit(
            "Electricity",
            480_000,
            category,
            room.rep.member_id,
            {room.lan.member_id: 6500, room.minh.member_id: 3500},
            SplitType.CUSTOM_RATIO,
        ),
    )
    assert updated.version == active.version + 1 and updated.agreed_count == 1
    assert updated.total_amount == 480_000
    assert updated.content_revision == 2 and active.content_revision == 1
    assert updated.payer_name == "Hao" and updated.category_name == "Utilities"
    assert updated.shares == {room.lan.member_id: 312_000, room.minh.member_id: 168_000}
    assert updated.review_deadline is None
    creator_view = await review(1, "refresh", active.version)
    assert creator_view.can_cancel and not creator_view.can_vote
    with pytest.raises(PermissionDeniedError):
        await review(1, "reject", updated.version, reason=RejectionReason.WRONG_AMOUNT)
    with pytest.raises(ConflictError):
        await review(1, "edit", active.version)
    with pytest.raises(ValidationError):
        await review(3, "reject", updated.version, reason=RejectionReason.OTHER)
    disputed = await review(
        3, "reject", updated.version, reason=RejectionReason.OTHER, note="Sai kỳ"
    )
    assert "Sai kỳ" in disputed.rejection and not disputed.can_edit
    assert disputed.can_add_reason
    more = await review(3, "addreason", disputed.version, reason=RejectionReason.DUPLICATE)
    assert more.status == "DISPUTED" and disputed.rejection in more.rejection
    assert len(more.rejection.splitlines()) == 2
    async with uow_factory() as uow:
        saved = await uow.expenses.get(created.expense_id)
        assert all(a.expense_version == more.version for a in saved.approvals)
    cancelled = await review(1, "cancel", more.version)
    assert cancelled.status == "CANCELLED"
    async with uow_factory() as uow:
        assert not await uow.ledger.list_by_expense(created.expense_id)


async def test_retry_after_confirmation_does_not_post_ledger_twice(uow_factory, session_factory):
    room = await make_room(uow_factory)
    expense = await make_expense(uow_factory, room, deadline=datetime.now(UTC) - timedelta(days=1))
    service = ExpenseService(uow_factory=uow_factory)
    await service.resolve_room(CHAT_ID)
    send = AsyncMock(side_effect=[TimeoutError(), None])
    assert await service.deliver_next(send)
    assert not await service.deliver_next(send)
    async with session_factory.begin() as session:
        job = (await session.scalars(select(ExpenseDelivery))).one()
        assert job.attempts == 1
        job.available_at = datetime.now(UTC) - timedelta(seconds=1)
    restarted = ExpenseService(uow_factory=uow_factory)
    assert await restarted.deliver_next(send)
    assert not await restarted.deliver_next(send)
    assert send.await_count == 2
    async with uow_factory() as uow:
        assert len(await uow.ledger.list_by_expense(expense.id)) == 3


async def test_dispute_reminders_repeat_until_cancel(uow_factory, session_factory):
    room = await make_room(uow_factory)
    expense = await make_expense(uow_factory, room)
    service = ExpenseService(uow_factory=uow_factory)
    args = dict(expense_id=expense.id, telegram_chat_id=CHAT_ID)
    start = datetime.now(UTC)
    disputed = await service.review(
        **args, telegram_user_id=2, version=1, action="reject", reason=RejectionReason.DUPLICATE
    )
    sent = []

    async def deliver(job, expense, review, chat_id, creator):
        sent.append((job.kind, job.recipient or creator))

    async def make_reminder_due():
        async with session_factory.begin() as session:
            job = (
                await session.scalars(
                    select(ExpenseDelivery).where(ExpenseDelivery.kind == "reminder")
                )
            ).one()
            assert job.available_at >= start + timedelta(days=3)
            job.available_at = start - timedelta(seconds=1)

    while await service.deliver_next(deliver):
        pass
    assert ("notice", 1) in sent and ("reminder", 1) not in sent
    await make_reminder_due()
    assert await service.deliver_next(deliver)
    assert sent[-1] == ("reminder", 1)
    await service.review(**args, telegram_user_id=1, version=disputed.version, action="cancel")
    await make_reminder_due()
    while await service.deliver_next(deliver):
        pass
    assert sent.count(("reminder", 1)) == 1


async def test_edit_notifies_added_and_removed_members_and_blocks_old_vote(
    uow_factory, session_factory
):
    room = await make_room(uow_factory)
    new = await RoomService(uow_factory).register_member(
        telegram_chat_id=CHAT_ID, chat_title="P302", telegram_user_id=4, display_name="An"
    )
    expense = await make_expense(uow_factory, room)
    service = ExpenseService(uow_factory=uow_factory)
    args = dict(expense_id=expense.id, telegram_chat_id=CHAT_ID, version=1)
    revised = await service.review(
        **args,
        telegram_user_id=1,
        action="edit",
        edit=ExpenseEdit(
            "Groceries",
            expense.total_amount,
            expense.category_id,
            room.rep.member_id,
            {key: 1 for key in (room.rep.member_id, room.lan.member_id, new.member_id)},
            SplitType.EQUAL,
        ),
    )
    async with session_factory() as session:
        notices = list(
            await session.scalars(select(ExpenseDelivery).where(ExpenseDelivery.kind == "notice"))
        )
        assert {n.recipient for n in notices} == {3, 4}
    with pytest.raises(ConflictError):
        await service.review(**args, telegram_user_id=3, action="agree")
    latest = await service.review(**args, telegram_user_id=3, action="refresh")
    assert latest.version == revised.version and latest.last_change and not latest.can_vote


async def test_late_vote_resolves_overdue_once(uow_factory):
    room = await make_room(uow_factory)
    deadline = datetime.now(UTC) - timedelta(minutes=1)
    expense = await make_expense(uow_factory, room, deadline=deadline)
    service = ExpenseService(uow_factory=uow_factory)
    with pytest.raises(ConflictError):
        await service.review(
            expense_id=expense.id,
            version=1,
            action="reject",
            reason=RejectionReason.WRONG_AMOUNT,
            telegram_chat_id=CHAT_ID,
            telegram_user_id=2,
        )
    assert await service.resolve_room(CHAT_ID) == []
    async with uow_factory() as uow:
        saved = await uow.expenses.get(expense.id)
        assert saved.auto_resolved and saved.confirmed_at == deadline
        entries = await uow.ledger.list_by_expense(expense.id)
        assert len(entries) == 3 and all(e.effective_at == deadline for e in entries)


@pytest.mark.parametrize("dispute", [False, True], ids=["agree", "reject-and-add-reason"])
async def test_review_missing_payer_and_split_member(uow_factory, monkeypatch, dispute):
    room = await make_room(uow_factory)
    expense = await make_expense(uow_factory, room)
    async with uow_factory() as uow:
        members = await uow.rooms.list_members(room.room_id)
    partial_room = SimpleNamespace(
        id=room.room_id,
        members=[m for m in members if m.id != room.rep.member_id],
    )
    monkeypatch.setattr(RoomRepository, "get_room_by_chat_id", AsyncMock(return_value=partial_room))
    service = ExpenseService(uow_factory=uow_factory)
    args = dict(
        expense_id=expense.id,
        telegram_chat_id=CHAT_ID,
        telegram_user_id=2,
    )
    if dispute:
        rejected = await service.review(
            **args, version=expense.version, action="reject", reason=RejectionReason.WRONG_AMOUNT
        )
        card = await service.review(
            **args, version=rejected.version, action="addreason", reason=RejectionReason.DUPLICATE
        )
        assert card.status == "DISPUTED" and len(card.rejection.splitlines()) == 2
    else:
        card = await service.review(**args, version=expense.version, action="agree")
        assert card.agreed_count == 1
    assert card.payer_name == "Thành viên"
    assert {s.display_name for s in card.splits} == {"Thành viên", "Lan", "Minh"}


async def test_concurrent_final_votes_post_once(uow_factory):
    room = await make_room(uow_factory)
    expense = await make_expense(uow_factory, room)
    service = ExpenseService(uow_factory=uow_factory)

    async def vote(user):
        return await service.review(
            expense_id=expense.id,
            version=1,
            telegram_chat_id=CHAT_ID,
            telegram_user_id=user,
            action="agree",
        )

    async with uow_factory() as uow:
        await uow.expenses.upsert_approval(
            expense_id=expense.id,
            member_id=room.rep.member_id,
            decision=ApprovalDecision.AGREE,
            expense_version=1,
        )
        await uow.commit()
    results = await asyncio.gather(vote(2), vote(3))
    assert sorted(result.status.value for result in results) == ["CONFIRMED", "PENDING"]
    async with uow_factory() as uow:
        assert len(await uow.ledger.list_by_expense(expense.id)) == 3


async def test_failed_post_rolls_back_confirmation(uow_factory, monkeypatch):
    room = await make_room(uow_factory)
    expense = await make_expense(uow_factory, room)
    service = ExpenseService(uow_factory=uow_factory)

    async def vote(user):
        return await service.review(
            expense_id=expense.id,
            version=1,
            telegram_chat_id=CHAT_ID,
            telegram_user_id=user,
            action="agree",
        )

    async with uow_factory() as uow:
        await uow.expenses.upsert_approval(
            expense_id=expense.id,
            member_id=room.rep.member_id,
            decision=ApprovalDecision.AGREE,
            expense_version=1,
        )
        await uow.commit()
    await vote(2)
    monkeypatch.setattr(service, "_post_ledger", AsyncMock(side_effect=RuntimeError("failed post")))
    with pytest.raises(RuntimeError, match="failed post"):
        await vote(3)
    async with uow_factory() as uow:
        saved = await uow.expenses.get(expense.id)
        assert saved.status == "PENDING" and saved.version == 1
        assert len(saved.approvals) == 2 and not await uow.ledger.list_by_expense(expense.id)


async def test_overdue_decline_and_manual_expense(uow_factory):
    room = await make_room(uow_factory)
    async with uow_factory() as uow:
        db_room = await uow.rooms.get_room(room.room_id)
        db_room.review_default_action = ReviewDefaultAction.DECLINE
        await uow.commit()
    late = await make_expense(uow_factory, room, deadline=datetime.now(UTC) - timedelta(minutes=1))
    manual = await make_expense(uow_factory, room)
    service = ExpenseService(uow_factory=uow_factory)
    assert await service.resolve_room(CHAT_ID) == [(late.id, 1)]
    async with uow_factory() as uow:
        assert (await uow.expenses.get(late.id)).status == "CANCELLED"
        assert (await uow.expenses.get(manual.id)).status == "PENDING"
        assert not await uow.ledger.net_balances(room.room_id)


async def test_edit_restarts_share_window_after_utilities(uow_factory):
    room = await make_room(uow_factory)
    start = datetime.now(UTC)
    expense = await make_expense(uow_factory, room, deadline=start + timedelta(days=1))
    async with uow_factory() as uow:
        saved = await uow.expenses.get(expense.id)
        saved.review_window_minutes = 4320
        utilities = await uow.rooms.get_category_by_name(room.room_id, "Utilities")
        await uow.commit()
    service = ExpenseService(uow_factory=uow_factory)

    async def edit(category_id, version, payer):
        return await service.review(
            expense_id=expense.id,
            telegram_chat_id=CHAT_ID,
            telegram_user_id=1,
            version=version,
            action="edit",
            edit=ExpenseEdit(
                "Dinner", 300_000, category_id, payer, {room.lan.member_id: 1}, SplitType.EQUAL
            ),
        )

    with pytest.raises(ValidationError):
        await edit(utilities.id, expense.version, room.lan.member_id)
    manual = await edit(utilities.id, expense.version, room.rep.member_id)
    assert manual.review_deadline is None
    before = datetime.now(UTC)
    eligible = await edit(expense.category_id, manual.version, room.rep.member_id)
    assert (
        before + timedelta(days=3)
        <= eligible.review_deadline
        <= datetime.now(UTC) + timedelta(days=3)
    )
