from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import ApprovalDecision, ExpenseStatus, RejectionReason
from app.db.models import ExpenseSplit
from tests.db.conftest import pytestmark  # noqa: F401
from tests.db.helpers import make_expense, make_room


async def test_add_and_get_expense_with_splits(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room, total=100_000)

    async with uow_factory() as uow:
        expense = await uow.expenses.get(created.id)

    assert expense.version == 1
    assert expense.status is ExpenseStatus.PENDING
    assert sorted(s.share_amount for s in expense.splits) == [33_333, 33_333, 33_334]
    assert sum(s.share_amount for s in expense.splits) == expense.total_amount


async def test_update_if_version_bumps_version_and_rejects_stale_writes(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)

    async with uow_factory() as uow:
        assert await uow.expenses.update_if_version(created.id, 1, description="Rice")
        assert not await uow.expenses.update_if_version(created.id, 1, description="Stale")
        await uow.commit()

    async with uow_factory() as uow:
        expense = await uow.expenses.get(created.id)
    assert (expense.version, expense.description) == (2, "Rice")


async def test_update_if_version_checks_expected_status(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)
    now = datetime.now(UTC)

    async with uow_factory() as uow:
        assert await uow.expenses.update_if_version(
            created.id,
            1,
            expected_statuses=[ExpenseStatus.PENDING],
            status=ExpenseStatus.CONFIRMED,
            confirmed_at=now,
        )
        # The same overdue expense seen by a second request is applied only once.
        assert not await uow.expenses.update_if_version(
            created.id, 2, expected_statuses=[ExpenseStatus.PENDING], status=ExpenseStatus.CANCELLED
        )
        await uow.commit()


async def test_concurrent_units_of_work_cannot_both_win(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)

    async with uow_factory() as first, uow_factory() as second:
        a = await first.expenses.get(created.id)
        b = await second.expenses.get(created.id)
        assert a.version == b.version == 1
        assert await first.expenses.update_if_version(created.id, a.version, description="A")
        await first.commit()
        assert not await second.expenses.update_if_version(created.id, b.version, description="B")


async def test_version_cannot_be_set_directly(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)
    async with uow_factory() as uow:
        with pytest.raises(ValueError):
            await uow.expenses.update_if_version(created.id, 1, version=10)


async def test_confirmed_status_requires_confirmed_at(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)
    async with uow_factory() as uow:
        with pytest.raises(IntegrityError):
            await uow.expenses.update_if_version(created.id, 1, status=ExpenseStatus.CONFIRMED)


async def test_list_overdue_returns_only_pending_past_deadline(uow_factory) -> None:
    room = await make_room(uow_factory)
    now = datetime.now(UTC)
    overdue = await make_expense(uow_factory, room, deadline=now - timedelta(minutes=1))
    await make_expense(uow_factory, room, deadline=now + timedelta(minutes=5))
    await make_expense(uow_factory, room, deadline=None)  # manual approval only
    disputed = await make_expense(uow_factory, room, deadline=now - timedelta(minutes=2))
    async with uow_factory() as uow:
        await uow.expenses.update_if_version(disputed.id, 1, status=ExpenseStatus.DISPUTED)
        await uow.commit()

    async with uow_factory() as uow:
        result = await uow.expenses.list_overdue(room.room_id, now)
    assert [e.id for e in result] == [overdue.id]


async def test_replace_splits(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room, total=90_000)

    async with uow_factory() as uow:
        expense = await uow.expenses.get(created.id)
        await uow.expenses.replace_splits(
            expense,
            [
                ExpenseSplit(member_id=room.rep.member_id, share_amount=60_000),
                ExpenseSplit(member_id=room.lan.member_id, share_amount=30_000),
            ],
        )
        await uow.commit()

    async with uow_factory() as uow:
        expense = await uow.expenses.get(created.id)
    assert {s.member_id: s.share_amount for s in expense.splits} == {
        room.rep.member_id: 60_000,
        room.lan.member_id: 30_000,
    }


async def test_zero_share_is_rejected(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)
    async with uow_factory() as uow:
        expense = await uow.expenses.get(created.id)
        with pytest.raises(IntegrityError):
            await uow.expenses.replace_splits(
                expense, [ExpenseSplit(member_id=room.rep.member_id, share_amount=0)]
            )


async def test_approvals_upsert_and_clear_except_editor(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)

    async with uow_factory() as uow:
        for member in (room.rep, room.lan):
            await uow.expenses.upsert_approval(
                expense_id=created.id,
                member_id=member.member_id,
                decision=ApprovalDecision.AGREE,
                expense_version=1,
            )
        rejected = await uow.expenses.upsert_approval(
            expense_id=created.id,
            member_id=room.lan.member_id,
            decision=ApprovalDecision.REJECT,
            expense_version=1,
            reason_code=RejectionReason.WRONG_AMOUNT,
            reason_note="It was 250k",
        )
        await uow.commit()

    assert rejected.decision is ApprovalDecision.REJECT
    async with uow_factory() as uow:
        approvals = await uow.expenses.list_approvals(created.id)
        assert len(approvals) == 2  # one row per member, Lan's was replaced
        assert (
            await uow.expenses.clear_approvals(created.id, keep_member_id=room.rep.member_id) == 1
        )
        await uow.commit()

    async with uow_factory() as uow:
        expense = await uow.expenses.get(created.id)
    assert [a.member_id for a in expense.approvals] == [room.rep.member_id]


async def test_reason_is_only_allowed_on_reject(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)
    async with uow_factory() as uow:
        with pytest.raises(IntegrityError):
            await uow.expenses.upsert_approval(
                expense_id=created.id,
                member_id=room.rep.member_id,
                decision=ApprovalDecision.AGREE,
                expense_version=1,
                reason_code=RejectionReason.DUPLICATE,
            )
