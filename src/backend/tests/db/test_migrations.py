from __future__ import annotations

import asyncio

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from alembic import command
from app.db.enums import ApprovalDecision
from app.db.models import Base
from app.services.expense_service import ExpenseService
from tests.db.conftest import (
    alembic_config,
    pytestmark,  # noqa: F401  (skip without TEST_DATABASE_URL)
)
from tests.db.helpers import CHAT_ID, make_expense, make_room


async def test_migration_creates_every_table(engine) -> None:
    async with engine.connect() as conn:
        tables = await conn.run_sync(lambda sync: set(inspect(sync).get_table_names()))
    assert set(Base.metadata.tables) | {"alembic_version"} == tables


async def test_models_and_migration_have_no_drift(engine) -> None:
    def diff(sync_conn):
        context = MigrationContext.configure(
            sync_conn, opts={"compare_type": True, "compare_server_default": True}
        )
        return compare_metadata(context, Base.metadata)

    async with engine.connect() as conn:
        assert await conn.run_sync(diff) == []


async def test_webhook_state_singleton_is_seeded(engine) -> None:
    async with engine.connect() as conn:
        rows = (await conn.execute(text("SELECT id, last_update_id FROM webhook_state"))).all()
    assert rows == [(1, 0)]


async def test_upgrade_repairs_legacy_creator_vote(migrated_database, uow_factory):
    room = await make_room(uow_factory)
    pending = await make_expense(uow_factory, room)
    unanimous = await make_expense(uow_factory, room)
    async with uow_factory() as uow:
        for expense, member in [
            (pending, room.lan),
            (unanimous, room.lan),
            (unanimous, room.minh),
        ]:
            await uow.expenses.upsert_approval(
                expense_id=expense.id,
                member_id=member.member_id,
                decision=ApprovalDecision.AGREE,
                expense_version=expense.version,
            )
        await uow.commit()

    config = alembic_config(migrated_database)
    for _ in range(2):
        await asyncio.to_thread(command.downgrade, config, "uc05delivery")
        await asyncio.to_thread(command.upgrade, config, "head")

    async with uow_factory() as uow:
        saved = await uow.expenses.get(unanimous.id)
        assert saved.status == "CONFIRMED" and saved.version == unanimous.version + 1
        assert len(saved.approvals) == 3
        assert all(a.expense_version == saved.version for a in saved.approvals)
        entries = await uow.ledger.list_by_expense(unanimous.id)
        assert sorted(e.amount_delta for e in entries) == [-100_000, -100_000, 200_000]
        saved = await uow.expenses.get(pending.id)
        assert saved.status == "PENDING" and saved.version == pending.version
        assert {a.member_id for a in saved.approvals} == {room.rep.member_id, room.lan.member_id}
        assert not await uow.ledger.list_by_expense(pending.id)

    final = await ExpenseService(uow_factory=uow_factory).review(
        expense_id=pending.id,
        version=pending.version,
        action="agree",
        telegram_chat_id=CHAT_ID,
        telegram_user_id=3,
    )
    assert final.status == "CONFIRMED"
