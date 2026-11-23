from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Persistence only: queries and writes, no business rules, never commits.

    The owning ``UnitOfWork`` commits once per use case. Methods ``flush`` when the caller
    needs server-generated values (ids, defaults) or constraint errors surfaced early.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
