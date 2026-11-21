from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import ExpenseStatus, LedgerEntryType
from app.db.models import LedgerEntry
from tests.db.conftest import pytestmark  # noqa: F401
from tests.db.helpers import make_expense, make_room


def _entries(room, expense, effective_at=None):
    kwargs = {"effective_at": effective_at} if effective_at else {}
    return [
        LedgerEntry(
            room_id=room.room_id,
            member_id=split.member_id,
            entry_type=LedgerEntryType.EXPENSE,
            expense_id=expense.id,
            amount_delta=(expense.total_amount - split.share_amount)
            if split.member_id == expense.payer_member_id
            else -split.share_amount,
            **kwargs,
        )
        for split in expense.splits
    ]


async def test_confirmation_writes_status_and_ledger_in_one_commit(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room, total=300_000)

    async with uow_factory() as uow:
        expense = await uow.expenses.get(created.id, for_update=True)
        assert await uow.expenses.update_if_version(
            expense.id,
            expense.version,
            expected_statuses=[ExpenseStatus.PENDING],
            status=ExpenseStatus.CONFIRMED,
            confirmed_at=datetime.now(UTC),
        )
        await uow.ledger.append_many(_entries(room, expense))
        await uow.commit()

    async with uow_factory() as uow:
        balances = await uow.ledger.net_balances(room.room_id)
        entries = await uow.ledger.list_by_expense(created.id)
    assert balances == {
        room.rep.member_id: 200_000,
        room.lan.member_id: -100_000,
        room.minh.member_id: -100_000,
    }
    assert sum(balances.values()) == 0
    assert len(entries) == 3


async def test_uncommitted_work_is_rolled_back(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)

    async with uow_factory() as uow:
        await uow.ledger.append_many(_entries(room, created))
        # no commit

    with pytest.raises(RuntimeError):
        async with uow_factory() as uow:
            await uow.ledger.append_many(_entries(room, created))
            raise RuntimeError("use case failed")

    async with uow_factory() as uow:
        assert await uow.ledger.net_balances(room.room_id) == {}


async def test_ledger_period_filter_uses_effective_at(uow_factory) -> None:
    room = await make_room(uow_factory)
    created = await make_expense(uow_factory, room)
    deadline = datetime.now(UTC) - timedelta(days=40)

    async with uow_factory() as uow:
        await uow.ledger.append_many(_entries(room, created, effective_at=deadline))
        await uow.commit()

    since = datetime.now(UTC) - timedelta(days=30)
    async with uow_factory() as uow:
        assert await uow.ledger.list_by_member(room.lan.member_id, since=since) == []
        old = await uow.ledger.list_by_member(room.lan.member_id)
    assert len(old) == 1
    assert old[0].effective_at == deadline
    assert old[0].created_at > deadline


async def test_ledger_entry_needs_exactly_one_source(uow_factory) -> None:
    room = await make_room(uow_factory)
    async with uow_factory() as uow:
        with pytest.raises(IntegrityError):
            await uow.ledger.append(
                LedgerEntry(
                    room_id=room.room_id,
                    member_id=room.rep.member_id,
                    entry_type=LedgerEntryType.EXPENSE,
                    amount_delta=1_000,
                )
            )


async def test_unit_of_work_is_not_reentrant(uow_factory) -> None:
    uow = uow_factory()
    async with uow:
        with pytest.raises(RuntimeError):
            await uow.__aenter__()
