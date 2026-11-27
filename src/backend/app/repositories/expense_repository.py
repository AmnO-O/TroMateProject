from __future__ import annotations

import uuid
from collections.abc import Collection, Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.db.enums import ApprovalDecision, ExpenseStatus, RejectionReason
from app.db.models import Attachment, Expense, ExpenseApproval, ExpenseSplit
from app.db.models.expense_model import ExpenseDelivery
from app.repositories.base_repository import BaseRepository


class ExpenseRepository(BaseRepository):
    """Expenses with their splits and approvals, plus receipt attachments."""

    async def get(self, expense_id: uuid.UUID, *, for_update: bool = False) -> Expense | None:
        """Load an expense with fresh ``splits`` and ``approvals``.

        ``populate_existing`` refreshes an instance already in the session, so calling
        ``get`` again after a write returns current data. ``for_update`` takes a row lock
        (``SELECT ... FOR UPDATE``) until the unit of work ends, for read-decide-write
        sequences such as "is this the last approval?".
        """

        stmt = (
            select(Expense)
            .where(Expense.id == expense_id)
            .execution_options(populate_existing=True)
        )
        if for_update:
            stmt = stmt.with_for_update(of=Expense)
        return (await self._session.scalars(stmt)).one_or_none()

    async def add(self, expense: Expense) -> Expense:
        """Insert an expense together with any ``splits``/``approvals`` attached to it."""

        self._session.add(expense)
        await self._session.flush()
        return expense

    async def list_by_room(
        self,
        room_id: uuid.UUID,
        *,
        statuses: Collection[ExpenseStatus] | None = None,
        limit: int | None = None,
    ) -> list[Expense]:
        stmt = select(Expense).where(Expense.room_id == room_id)
        if statuses:
            stmt = stmt.where(Expense.status.in_(list(statuses)))
        stmt = stmt.order_by(Expense.created_at.desc(), Expense.id)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list((await self._session.scalars(stmt)).all())

    async def list_overdue(self, room_id: uuid.UUID, now: datetime) -> list[Expense]:
        """PENDING expenses of a room whose review deadline is at or before ``now``."""

        stmt = (
            select(Expense)
            .where(
                Expense.room_id == room_id,
                Expense.status == ExpenseStatus.PENDING,
                Expense.review_deadline.is_not(None),
                Expense.review_deadline <= now,
            )
            .order_by(Expense.review_deadline, Expense.id)
        )
        return list((await self._session.scalars(stmt)).all())

    async def update_if_version(
        self,
        expense_id: uuid.UUID,
        expected_version: int,
        *,
        expected_statuses: Collection[ExpenseStatus] | None = None,
        **values: Any,
    ) -> bool:
        """Optimistic-locking write: ``UPDATE expenses SET ..., version = version + 1
        WHERE id = :id AND version = :expected [AND status IN (...)]``.

        Returns ``False`` when no row matched (stale version or status already changed);
        the caller turns that into a 409 Conflict. ``version`` cannot be set directly.
        """

        if "version" in values:
            raise ValueError("version is incremented automatically")
        stmt = (
            update(Expense)
            .where(Expense.id == expense_id, Expense.version == expected_version)
            .values(**values, version=Expense.version + 1)
            .returning(Expense.id)
            .execution_options(synchronize_session="fetch")
        )
        if expected_statuses:
            stmt = stmt.where(Expense.status.in_(list(expected_statuses)))
        return (await self._session.execute(stmt)).first() is not None

    async def replace_splits(self, expense: Expense, splits: Iterable[ExpenseSplit]) -> None:
        """Replace every split of ``expense`` (used when an edit changes the split)."""

        expense.splits.clear()
        await self._session.flush()  # delete old rows before inserting (unique per member)
        expense.splits.extend(splits)
        await self._session.flush()

    # --- approvals -----------------------------------------------------------

    async def upsert_approval(
        self,
        *,
        expense_id: uuid.UUID,
        member_id: uuid.UUID,
        decision: ApprovalDecision,
        expense_version: int,
        reason_code: RejectionReason | None = None,
        reason_note: str | None = None,
    ) -> ExpenseApproval:
        """Insert or replace the member's single approval row for the expense."""

        values = {
            "decision": decision,
            "expense_version": expense_version,
            "reason_code": reason_code,
            "reason_note": reason_note,
        }
        stmt = (
            insert(ExpenseApproval)
            .values(id=uuid.uuid4(), expense_id=expense_id, member_id=member_id, **values)
            .on_conflict_do_update(
                index_elements=[ExpenseApproval.expense_id, ExpenseApproval.member_id],
                set_={**values, "voted_at": func.now()},
            )
            .returning(ExpenseApproval)
            .execution_options(populate_existing=True)
        )
        return (await self._session.scalars(stmt)).one()

    async def list_approvals(
        self, expense_id: uuid.UUID, *, expense_version: int | None = None
    ) -> list[ExpenseApproval]:
        stmt = select(ExpenseApproval).where(ExpenseApproval.expense_id == expense_id)
        if expense_version is not None:
            stmt = stmt.where(ExpenseApproval.expense_version == expense_version)
        stmt = stmt.order_by(ExpenseApproval.voted_at).execution_options(populate_existing=True)
        return list((await self._session.scalars(stmt)).all())

    async def clear_approvals(
        self, expense_id: uuid.UUID, *, keep_member_id: uuid.UUID | None = None
    ) -> int:
        """Delete approvals of an expense, optionally keeping one member's (the editor's)."""

        stmt = delete(ExpenseApproval).where(ExpenseApproval.expense_id == expense_id)
        if keep_member_id is not None:
            stmt = stmt.where(ExpenseApproval.member_id != keep_member_id)
        result = await self._session.execute(stmt.execution_options(synchronize_session="fetch"))
        return result.rowcount or 0

    # --- attachments ---------------------------------------------------------

    async def add_attachment(self, attachment: Attachment) -> Attachment:
        self._session.add(attachment)
        await self._session.flush()
        return attachment

    async def get_attachment(self, attachment_id: uuid.UUID) -> Attachment | None:
        return await self._session.get(Attachment, attachment_id)

    def enqueue(self, expense, kind="card", *, recipient=None, body="", available_at=None):
        delivery = ExpenseDelivery(
            expense_id=expense.id,
            revision=expense.content_revision,
            kind=kind,
            recipient=recipient,
            body=body,
        )
        if available_at is not None:
            delivery.available_at = available_at
        self._session.add(delivery)

    async def next_delivery(self, now):
        stmt = (
            select(ExpenseDelivery)
            .where(ExpenseDelivery.available_at <= now)
            .order_by(ExpenseDelivery.available_at, ExpenseDelivery.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return (await self._session.scalars(stmt)).one_or_none()

    async def finish_delivery(self, delivery):
        await self._session.delete(delivery)
