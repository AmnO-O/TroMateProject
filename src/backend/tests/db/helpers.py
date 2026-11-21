from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.db.enums import ExpenseStatus, SourceType, SplitType
from app.db.models import Expense, ExpenseSplit
from app.services import Membership, RoomService

CHAT_ID = -1001234567890


@dataclass
class RoomFixture:
    rep: Membership
    lan: Membership
    minh: Membership

    @property
    def room_id(self):
        return self.rep.room_id


async def make_room(uow_factory) -> RoomFixture:
    service = RoomService(uow_factory)
    common = {"telegram_chat_id": CHAT_ID, "chat_title": "P302"}
    rep = await service.register_member(**common, telegram_user_id=1, display_name="Hao")
    lan = await service.register_member(**common, telegram_user_id=2, display_name="Lan")
    minh = await service.register_member(**common, telegram_user_id=3, display_name="Minh")
    return RoomFixture(rep=rep, lan=lan, minh=minh)


async def make_expense(
    uow_factory,
    room: RoomFixture,
    *,
    total: int = 300_000,
    deadline: datetime | None = None,
    status: ExpenseStatus = ExpenseStatus.PENDING,
) -> Expense:
    async with uow_factory() as uow:
        category = await uow.rooms.get_category_by_name(room.room_id, "groceries")
        share = total // 3
        expense = Expense(
            room_id=room.room_id,
            category_id=category.id,
            created_by_member_id=room.rep.member_id,
            payer_member_id=room.rep.member_id,
            description="Groceries",
            total_amount=total,
            split_type=SplitType.EQUAL,
            source_type=SourceType.TEXT,
            status=status,
            review_deadline=deadline,
            review_window_minutes=5 if deadline else None,
            splits=[
                ExpenseSplit(member_id=room.rep.member_id, share_amount=total - 2 * share),
                ExpenseSplit(member_id=room.lan.member_id, share_amount=share),
                ExpenseSplit(member_id=room.minh.member_id, share_amount=share),
            ],
        )
        await uow.expenses.add(expense)
        await uow.commit()
        return expense
