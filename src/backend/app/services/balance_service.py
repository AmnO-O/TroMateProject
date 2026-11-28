"""Live room balances and expense history for ``/balance`` and the Mini App (SCRUM-125)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.enums import ExpenseStatus
from app.db.models import Room, RoomMember
from app.db.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.services.debt_engine import simplify_debts
from app.services.errors import PermissionDeniedError

# DRAFT rows are not shared with the room yet, so they never appear in the history.
LISTED_STATUSES: tuple[ExpenseStatus, ...] = (
    ExpenseStatus.PENDING,
    ExpenseStatus.DISPUTED,
    ExpenseStatus.CONFIRMED,
    ExpenseStatus.CANCELLED,
)
DEFAULT_EXPENSE_LIMIT = 20
MAX_EXPENSE_LIMIT = 100


@dataclass(frozen=True, slots=True)
class MemberBalance:
    """Net balance of one member; ``+`` the room owes them, ``-`` they owe the room."""

    member_id: uuid.UUID
    telegram_user_id: int
    display_name: str
    amount: int


@dataclass(frozen=True, slots=True)
class SuggestedTransfer:
    from_member_id: uuid.UUID
    from_name: str
    to_member_id: uuid.UUID
    to_name: str
    amount: int


@dataclass(frozen=True, slots=True)
class RoomBalances:
    room_id: uuid.UUID
    room_name: str
    telegram_chat_id: int
    balances: tuple[MemberBalance, ...]
    transfers: tuple[SuggestedTransfer, ...]
    viewer_member_id: uuid.UUID | None
    generated_at: datetime

    @property
    def is_settled(self) -> bool:
        return all(item.amount == 0 for item in self.balances)


@dataclass(frozen=True, slots=True)
class ExpenseRecord:
    expense_id: uuid.UUID
    description: str
    total_amount: int
    payer_name: str
    category_name: str
    status: ExpenseStatus
    created_at: datetime
    confirmed_at: datetime | None
    viewer_share: int | None


class BalanceService:
    """Reads net balances from ``ledger_entries`` (IBalanceService in SCRUM-116).

    Only CONFIRMED expenses (and settlements) are written to the ledger, so summing the
    ledger gives the live balance. Overdue PENDING expenses are confirmed lazily by
    ``ExpenseService.resolve_room``; callers run that first so the figures are current.
    """

    def __init__(self, uow_factory: UnitOfWorkFactory = UnitOfWork) -> None:
        self._uow_factory = uow_factory

    async def get_room_balances(
        self, telegram_chat_id: int, *, telegram_user_id: int | None = None
    ) -> RoomBalances | None:
        """Balances of every member plus suggested transfers; ``None`` if the room is unknown.

        With ``telegram_user_id`` the caller must be a member of the room (Mini App); the
        group ``/balance`` command passes ``None`` because its reply is visible to the chat.
        """

        async with self._uow_factory() as uow:
            loaded = await _load_room(uow, telegram_chat_id, telegram_user_id)
            if loaded is None:
                return None
            room, viewer = loaded
            net = await uow.ledger.net_balances(room.id)

        balances = sorted(
            (
                MemberBalance(
                    member_id=member.id,
                    telegram_user_id=member.user.telegram_user_id,
                    display_name=member.user.display_name,
                    amount=net.get(member.id, 0),
                )
                for member in room.members
            ),
            key=lambda item: (-item.amount, item.display_name.casefold(), str(item.member_id)),
        )
        names = {item.member_id: item.display_name for item in balances}
        transfers = tuple(
            SuggestedTransfer(
                from_member_id=t.debtor,
                from_name=names.get(t.debtor, "Thành viên"),
                to_member_id=t.creditor,
                to_name=names.get(t.creditor, "Thành viên"),
                amount=t.amount,
            )
            for t in simplify_debts({item.member_id: item.amount for item in balances})
        )
        return RoomBalances(
            room_id=room.id,
            room_name=room.name,
            telegram_chat_id=room.telegram_chat_id,
            balances=tuple(balances),
            transfers=transfers,
            viewer_member_id=viewer.id if viewer else None,
            generated_at=datetime.now(UTC),
        )

    async def list_expenses(
        self,
        telegram_chat_id: int,
        *,
        telegram_user_id: int,
        limit: int = DEFAULT_EXPENSE_LIMIT,
    ) -> tuple[ExpenseRecord, ...] | None:
        """Newest shared expenses of the room, with the caller's own share of each."""

        limit = max(1, min(limit, MAX_EXPENSE_LIMIT))
        async with self._uow_factory() as uow:
            loaded = await _load_room(uow, telegram_chat_id, telegram_user_id)
            if loaded is None:
                return None
            room, viewer = loaded
            expenses = await uow.expenses.list_by_room(
                room.id, statuses=LISTED_STATUSES, limit=limit
            )
            categories = {
                c.id: c.name
                for c in await uow.rooms.list_categories(room.id, include_archived=True)
            }

        names = {member.id: member.user.display_name for member in room.members}
        viewer_id = viewer.id if viewer else None
        return tuple(
            ExpenseRecord(
                expense_id=expense.id,
                description=expense.description,
                total_amount=expense.total_amount,
                payer_name=names.get(expense.payer_member_id, "Thành viên"),
                category_name=categories.get(expense.category_id, ""),
                status=expense.status,
                created_at=expense.created_at,
                confirmed_at=expense.confirmed_at,
                viewer_share=next(
                    (s.share_amount for s in expense.splits if s.member_id == viewer_id), None
                ),
            )
            for expense in expenses
        )


async def _load_room(
    uow: UnitOfWork, telegram_chat_id: int, telegram_user_id: int | None
) -> tuple[Room, RoomMember | None] | None:
    room = await uow.rooms.get_room_by_chat_id(telegram_chat_id)
    if room is None:
        return None
    if telegram_user_id is None:
        return room, None
    viewer = next((m for m in room.members if m.user.telegram_user_id == telegram_user_id), None)
    if viewer is None:
        raise PermissionDeniedError("Bạn không thuộc phòng này.")
    return room, viewer
