from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import func, select, update

from app.db.models import Category, Room, RoomMember, User
from app.repositories.base_repository import BaseRepository


class RoomRepository(BaseRepository):
    """Rooms, users, room members and categories."""

    # --- rooms ---------------------------------------------------------------

    async def get_room(self, room_id: uuid.UUID) -> Room | None:
        return await self._session.get(Room, room_id)

    async def get_room_by_chat_id(self, telegram_chat_id: int) -> Room | None:
        stmt = select(Room).where(Room.telegram_chat_id == telegram_chat_id)
        return (await self._session.scalars(stmt)).one_or_none()

    async def add_room(self, room: Room) -> Room:
        self._session.add(room)
        await self._session.flush()
        return room

    async def try_consume_scan(self, room_id: uuid.UUID) -> bool:
        """Atomically take one image scan; ``False`` when none are left (BR08)."""

        stmt = (
            update(Room)
            .where(Room.id == room_id, Room.scans_remaining > 0)
            .values(scans_remaining=Room.scans_remaining - 1)
            .returning(Room.id)
            .execution_options(synchronize_session="fetch")
        )
        return (await self._session.execute(stmt)).first() is not None

    # --- users ---------------------------------------------------------------

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_user_by_telegram_id(self, telegram_user_id: int) -> User | None:
        stmt = select(User).where(User.telegram_user_id == telegram_user_id)
        return (await self._session.scalars(stmt)).one_or_none()

    async def add_user(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    # --- members -------------------------------------------------------------

    async def get_member(self, member_id: uuid.UUID) -> RoomMember | None:
        return await self._session.get(RoomMember, member_id)

    async def get_member_by_user(self, room_id: uuid.UUID, user_id: uuid.UUID) -> RoomMember | None:
        stmt = select(RoomMember).where(
            RoomMember.room_id == room_id, RoomMember.user_id == user_id
        )
        return (await self._session.scalars(stmt)).one_or_none()

    async def list_members(self, room_id: uuid.UUID) -> list[RoomMember]:
        stmt = (
            select(RoomMember)
            .where(RoomMember.room_id == room_id)
            .order_by(RoomMember.joined_at, RoomMember.id)
        )
        return list((await self._session.scalars(stmt)).all())

    async def list_memberships_of_user(self, user_id: uuid.UUID) -> list[RoomMember]:
        stmt = (
            select(RoomMember).where(RoomMember.user_id == user_id).order_by(RoomMember.joined_at)
        )
        return list((await self._session.scalars(stmt)).all())

    async def count_members(self, room_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(RoomMember).where(RoomMember.room_id == room_id)
        return (await self._session.scalar(stmt)) or 0

    async def add_member(self, member: RoomMember) -> RoomMember:
        self._session.add(member)
        await self._session.flush()
        return member

    # --- categories ----------------------------------------------------------

    async def get_category(self, category_id: uuid.UUID) -> Category | None:
        return await self._session.get(Category, category_id)

    async def get_category_by_name(self, room_id: uuid.UUID, name: str) -> Category | None:
        """Case-insensitive lookup, matching the unique index on ``lower(name)``."""

        stmt = select(Category).where(
            Category.room_id == room_id, func.lower(Category.name) == name.strip().lower()
        )
        return (await self._session.scalars(stmt)).one_or_none()

    async def list_categories(
        self, room_id: uuid.UUID, *, include_archived: bool = False
    ) -> list[Category]:
        stmt = select(Category).where(Category.room_id == room_id)
        if not include_archived:
            stmt = stmt.where(Category.is_archived.is_(False))
        stmt = stmt.order_by(Category.is_default.desc(), Category.created_at, Category.name)
        return list((await self._session.scalars(stmt)).all())

    async def add_categories(self, categories: Iterable[Category]) -> list[Category]:
        items = list(categories)
        self._session.add_all(items)
        await self._session.flush()
        return items
