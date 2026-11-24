"""Application service for UC01: Log Shared Expense via natural language text."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.adapters.ai_extraction import AIExtractionAdapter
from app.db.enums import ExpenseStatus, SourceType
from app.db.models import Expense, ExpenseSplit
from app.db.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.services.errors import NotFoundError
from app.services.expense_parser import ExpenseParser, MemberContext
from app.services.room_service import RoomService


@dataclass(frozen=True, slots=True)
class CreatedSplitLine:
    member_id: uuid.UUID
    display_name: str
    share_amount: int


@dataclass(frozen=True, slots=True)
class CreatedExpense:
    """Summary of a newly persisted ``PENDING`` expense for bot card rendering."""

    expense_id: uuid.UUID
    version: int
    description: str
    total_amount: int
    payer_name: str
    category_name: str
    status: ExpenseStatus
    splits: tuple[CreatedSplitLine, ...]
    review_deadline: datetime | None
    extraction_source: str


class ExpenseService:
    """Orchestrates extraction -> parsing -> PostgreSQL persistence for UC01."""

    def __init__(
        self,
        *,
        extractor: AIExtractionAdapter | None = None,
        parser: ExpenseParser | None = None,
        room_service: RoomService | None = None,
        uow_factory: UnitOfWorkFactory = UnitOfWork,
    ) -> None:
        self._extractor = extractor or AIExtractionAdapter()
        self._parser = parser or ExpenseParser()
        self._uow_factory = uow_factory
        self._room_service = room_service or RoomService(uow_factory=uow_factory)

    async def log_expense_from_text(
        self,
        *,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        sender_display_name: str,
        sender_username: str | None,
        text: str,
    ) -> CreatedExpense | None:
        """Extract, parse, and persist a ``PENDING`` expense from natural Vietnamese text."""

        raw = await self._extractor.extract(text)
        if raw is None:
            return None

        membership = await self._room_service.register_member(
            telegram_chat_id=telegram_chat_id,
            chat_title=chat_title,
            telegram_user_id=telegram_user_id,
            display_name=sender_display_name,
            username=sender_username,
        )

        async with self._uow_factory() as uow:
            room = await uow.rooms.get_room(membership.room_id)
            if room is None:
                raise NotFoundError("Room not found")

            members = await uow.rooms.list_members(room.id)
            member_contexts = [
                MemberContext(
                    member_id=m.id,
                    display_name=m.user.display_name,
                    username=m.user.username,
                )
                for m in members
            ]
            names_by_member_id = {m.member_id: m.display_name for m in member_contexts}

            # Feed Subtask 1 RawExtractionResult directly into Subtask 2 ExpenseParser
            parsed = self._parser.parse(
                raw,
                sender_member_id=membership.member_id,
                room_members=member_contexts,
            )

            category = await uow.rooms.get_category_by_name(room.id, parsed.category_name)
            if category is None or category.is_archived:
                category = await uow.rooms.get_category_by_name(room.id, "Other")
            if category is None:
                raise NotFoundError("Default 'Other' category missing for room")

            # BR02: Rent expenses require manual approval (no auto-confirm deadline).
            if category.name == "Rent":
                review_window = None
                review_deadline = None
            else:
                review_window = room.review_timeout_minutes
                review_deadline = datetime.now(UTC) + timedelta(minutes=review_window)

            expense = Expense(
                room_id=room.id,
                category_id=category.id,
                created_by_member_id=membership.member_id,
                payer_member_id=parsed.payer_member_id,
                description=parsed.description,
                total_amount=parsed.total_amount,
                split_type=parsed.split_type,
                status=ExpenseStatus.PENDING,
                source_type=SourceType.TEXT,
                review_window_minutes=review_window,
                review_deadline=review_deadline,
                splits=[
                    ExpenseSplit(
                        member_id=split.member_id,
                        share_amount=split.share_amount,
                    )
                    for split in parsed.splits
                ],
            )
            await uow.expenses.add(expense)
            await uow.commit()

            return CreatedExpense(
                expense_id=expense.id,
                version=expense.version,
                description=expense.description,
                total_amount=expense.total_amount,
                payer_name=names_by_member_id.get(expense.payer_member_id, sender_display_name),
                category_name=category.name,
                status=expense.status,
                splits=tuple(
                    CreatedSplitLine(
                        member_id=split.member_id,
                        display_name=names_by_member_id.get(split.member_id, "Member"),
                        share_amount=split.share_amount,
                    )
                    for split in parsed.splits
                ),
                review_deadline=expense.review_deadline,
                extraction_source=raw.source,
            )
