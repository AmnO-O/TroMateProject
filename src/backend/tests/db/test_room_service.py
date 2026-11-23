from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.enums import DEFAULT_CATEGORIES, MemberRole
from app.db.models import Category, RoomMember
from app.services import RoomService
from tests.db.conftest import pytestmark  # noqa: F401
from tests.db.helpers import CHAT_ID, make_room


async def test_first_member_creates_room_with_defaults_and_becomes_rep(uow_factory) -> None:
    room = await make_room(uow_factory)

    assert room.rep.room_created and room.rep.role is MemberRole.ROOM_REP
    assert not room.lan.room_created and room.lan.role is MemberRole.MEMBER
    categories = await RoomService(uow_factory).list_active_categories(room.room_id)
    # Seeded in one transaction, so they share created_at and are ordered by name.
    assert [c.name for c in categories] == sorted(DEFAULT_CATEGORIES)
    assert all(c.is_default for c in categories)


async def test_register_member_is_idempotent_and_refreshes_profile(uow_factory) -> None:
    service = RoomService(uow_factory)
    first = await service.register_member(
        telegram_chat_id=CHAT_ID, chat_title="P302", telegram_user_id=7, display_name="Nam"
    )
    again = await service.register_member(
        telegram_chat_id=CHAT_ID,
        chat_title="P302",
        telegram_user_id=7,
        display_name="Nam P.",
        username="nam_p",
    )

    assert again.member_id == first.member_id
    assert not again.member_created
    async with uow_factory() as uow:
        user = await uow.rooms.get_user(first.user_id)
        assert (user.display_name, user.username) == ("Nam P.", "nam_p")
        assert await uow.rooms.count_members(first.room_id) == 1


async def test_only_one_room_rep_per_room(uow_factory) -> None:
    room = await make_room(uow_factory)
    async with uow_factory() as uow:
        member = await uow.rooms.get_member(room.lan.member_id)
        member.role = MemberRole.ROOM_REP
        with pytest.raises(IntegrityError):
            await uow.flush()


async def test_category_names_are_unique_ignoring_case(uow_factory) -> None:
    room = await make_room(uow_factory)
    async with uow_factory() as uow:
        assert (await uow.rooms.get_category_by_name(room.room_id, "  FOOD & drinks ")) is not None
        with pytest.raises(IntegrityError):
            await uow.rooms.add_categories([Category(room_id=room.room_id, name="RENT")])


async def test_scans_are_consumed_atomically_until_zero(uow_factory) -> None:
    room = await make_room(uow_factory)
    async with uow_factory() as uow:
        results = [await uow.rooms.try_consume_scan(room.room_id) for _ in range(11)]
        await uow.commit()
    assert results == [True] * 10 + [False]
    async with uow_factory() as uow:
        assert (await uow.rooms.get_room(room.room_id)).scans_remaining == 0


async def test_room_members_relationship_is_eager_loaded(uow_factory) -> None:
    room = await make_room(uow_factory)
    async with uow_factory() as uow:
        loaded = await uow.rooms.get_room(room.room_id)
        names = [m.user.display_name for m in loaded.members]
    assert names == ["Hao", "Lan", "Minh"]
    assert all(isinstance(m, RoomMember) for m in loaded.members)
