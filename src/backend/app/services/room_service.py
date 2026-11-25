from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.db.enums import DEFAULT_CATEGORIES, MemberRole
from app.db.models import Category, Room, RoomMember, User
from app.db.unit_of_work import UnitOfWork, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class Membership:
    room_id: uuid.UUID
    member_id: uuid.UUID
    user_id: uuid.UUID
    role: MemberRole
    room_created: bool
    member_created: bool


@dataclass(frozen=True, slots=True)
class CategoryInfo:
    id: uuid.UUID
    name: str
    is_default: bool


class RoomService:
    """Rooms, members and categories (IRoomService in SCRUM-116).

    Holds the business rules; repositories only persist. Each public method is one use case
    and commits once.
    """

    def __init__(self, uow_factory: UnitOfWorkFactory = UnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def register_member(
        self,
        *,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        display_name: str,
        username: str | None = None,
    ) -> Membership:
        """Get or create the room for a Telegram group and the sender's membership.

        A new room is seeded with the BR06 default categories, and its first member becomes
        the Room Rep (BR09: each room has exactly one Room Rep). Two first messages racing
        for the same new chat hit a unique constraint; the loser retries and joins.
        """

        try:
            return await self._register_member_once(
                telegram_chat_id, chat_title, telegram_user_id, display_name, username
            )
        except IntegrityError:
            return await self._register_member_once(
                telegram_chat_id, chat_title, telegram_user_id, display_name, username
            )

    async def list_active_categories(self, room_id: uuid.UUID) -> list[CategoryInfo]:
        async with self._uow_factory() as uow:
            categories = await uow.rooms.list_categories(room_id)
        return [CategoryInfo(id=c.id, name=c.name, is_default=c.is_default) for c in categories]

    async def ensure_room_and_member_in_uow(
        self,
        uow: UnitOfWork,
        *,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        display_name: str,
        username: str | None = None,
    ) -> tuple[Room, RoomMember, bool, bool]:
        """Resolve or create room + sender inside an existing ``UnitOfWork``.

        Loads the room once (with eager-loaded ``room.members``) and checks the sender in
        memory so warm requests avoid separate user/member round-trips.
        """

        room = await uow.rooms.get_room_by_chat_id(telegram_chat_id)
        if room is not None:
            sender = next(
                (m for m in room.members if m.user.telegram_user_id == telegram_user_id),
                None,
            )
            if sender is not None:
                if (sender.user.username, sender.user.display_name) != (username, display_name):
                    sender.user.username = username
                    sender.user.display_name = display_name
                return room, sender, False, False

        user = await uow.rooms.get_user_by_telegram_id(telegram_user_id)
        if user is None:
            user = await uow.rooms.add_user(
                User(
                    telegram_user_id=telegram_user_id,
                    username=username,
                    display_name=display_name,
                )
            )
        elif (user.username, user.display_name) != (username, display_name):
            user.username = username
            user.display_name = display_name

        room_created = room is None
        if room is None:
            room = await uow.rooms.add_room(
                Room(telegram_chat_id=telegram_chat_id, name=chat_title[:128], members=[])
            )
            await uow.rooms.add_categories(
                Category(room_id=room.id, name=name, is_default=True)
                for name in DEFAULT_CATEGORIES
            )

        member = await uow.rooms.get_member_by_user(room.id, user.id)
        member_created = member is None
        if member is None:
            is_first = room_created or len(room.members) == 0
            member = await uow.rooms.add_member(
                RoomMember(
                    room_id=room.id,
                    user_id=user.id,
                    user=user,
                    role=MemberRole.ROOM_REP if is_first else MemberRole.MEMBER,
                )
            )
            room.members.append(member)

        return room, member, room_created, member_created

    async def _register_member_once(
        self,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        display_name: str,
        username: str | None,
    ) -> Membership:
        async with self._uow_factory() as uow:
            room, member, room_created, member_created = await self.ensure_room_and_member_in_uow(
                uow,
                telegram_chat_id=telegram_chat_id,
                chat_title=chat_title,
                telegram_user_id=telegram_user_id,
                display_name=display_name,
                username=username,
            )
            await uow.commit()
            return Membership(
                room_id=room.id,
                member_id=member.id,
                user_id=member.user_id,
                role=member.role,
                room_created=room_created,
                member_created=member_created,
            )
