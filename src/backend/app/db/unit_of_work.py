"""Unit of Work: one ``AsyncSession`` per request/update, one commit per use case."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_session_factory
from app.repositories import ExpenseRepository, LedgerRepository, RoomRepository


class UnitOfWork:
    """Groups repositories over a single session and transaction.

    Usage in a service::

        async with self._uow_factory() as uow:
            room = await uow.rooms.get_room(room_id)
            ...
            await uow.commit()

    Anything not committed when the block exits (normally or by exception) is rolled back,
    so a confirmation writes the expense status and its ledger entries together or not at
    all (business rule 1 in SCRUM-116).
    """

    rooms: RoomRepository
    expenses: ExpenseRepository
    ledger: LedgerRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("UnitOfWork is already active; create a new one per use case")
        factory = self._session_factory or get_session_factory()
        self._session = factory()
        self.rooms = RoomRepository(self._session)
        self.expenses = ExpenseRepository(self._session)
        self.ledger = LedgerRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        session = self._require_session()
        try:
            if exc_type is not None:
                await session.rollback()
        finally:
            # close() releases the connection and discards any uncommitted transaction
            # without expiring loaded objects, so committed results stay readable.
            await session.close()
            self._session = None

    async def commit(self) -> None:
        await self._require_session().commit()

    async def rollback(self) -> None:
        await self._require_session().rollback()

    async def flush(self) -> None:
        await self._require_session().flush()

    def _require_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork used outside 'async with'")
        return self._session


UnitOfWorkFactory = Callable[[], UnitOfWork]
