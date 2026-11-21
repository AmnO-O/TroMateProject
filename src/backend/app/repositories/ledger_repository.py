from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import Select, func, select

from app.db.models import LedgerEntry
from app.repositories.base_repository import BaseRepository


class LedgerRepository(BaseRepository):
    """Append-only access to ``ledger_entries``.

    There is deliberately no update or delete method: the ledger is immutable and
    corrections are written as compensating entries (SCRUM-117 section 3.3).
    """

    async def append(self, entry: LedgerEntry) -> LedgerEntry:
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def append_many(self, entries: Iterable[LedgerEntry]) -> list[LedgerEntry]:
        items = list(entries)
        self._session.add_all(items)
        await self._session.flush()
        return items

    async def list_by_room(
        self,
        room_id: uuid.UUID,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[LedgerEntry]:
        stmt = _in_period(select(LedgerEntry).where(LedgerEntry.room_id == room_id), since, until)
        return list((await self._session.scalars(_newest_first(stmt))).all())

    async def list_by_member(
        self,
        member_id: uuid.UUID,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[LedgerEntry]:
        stmt = _in_period(
            select(LedgerEntry).where(LedgerEntry.member_id == member_id), since, until
        )
        return list((await self._session.scalars(_newest_first(stmt))).all())

    async def list_by_expense(self, expense_id: uuid.UUID) -> list[LedgerEntry]:
        stmt = select(LedgerEntry).where(LedgerEntry.expense_id == expense_id)
        return list((await self._session.scalars(_newest_first(stmt))).all())

    async def net_balances(self, room_id: uuid.UUID) -> dict[uuid.UUID, int]:
        """Sum of ``amount_delta`` per member of the room (members with entries only)."""

        stmt = (
            select(LedgerEntry.member_id, func.sum(LedgerEntry.amount_delta))
            .where(LedgerEntry.room_id == room_id)
            .group_by(LedgerEntry.member_id)
        )
        rows = await self._session.execute(stmt)
        return {member_id: int(total) for member_id, total in rows.all()}


def _in_period(
    stmt: Select[tuple[LedgerEntry]], since: datetime | None, until: datetime | None
) -> Select[tuple[LedgerEntry]]:
    if since is not None:
        stmt = stmt.where(LedgerEntry.effective_at >= since)
    if until is not None:
        stmt = stmt.where(LedgerEntry.effective_at < until)
    return stmt


def _newest_first(stmt: Select[tuple[LedgerEntry]]) -> Select[tuple[LedgerEntry]]:
    return stmt.order_by(LedgerEntry.effective_at.desc(), LedgerEntry.id)
