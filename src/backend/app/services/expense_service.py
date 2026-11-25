"""Application service for UC01: Log Shared Expense via natural language text."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.adapters.ai_extraction import AIExtractionAdapter
from app.adapters.vnd_parser import RawExtractionResult
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
    """Orchestrates extraction -> parsing -> single-UoW PostgreSQL persistence for UC01."""

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
        """Extract, parse, and persist a ``PENDING`` expense in a single DB transaction."""

        raw = await self._extractor.extract(text)
        if raw is None:
            return None

        try:
            return await self._log_expense_once(
                raw=raw,
                telegram_chat_id=telegram_chat_id,
                chat_title=chat_title,
                telegram_user_id=telegram_user_id,
                sender_display_name=sender_display_name,
                sender_username=sender_username,
            )
        except IntegrityError:
            return await self._log_expense_once(
                raw=raw,
                telegram_chat_id=telegram_chat_id,
                chat_title=chat_title,
                telegram_user_id=telegram_user_id,
                sender_display_name=sender_display_name,
                sender_username=sender_username,
            )

    async def _log_expense_once(
        self,
        *,
        raw: RawExtractionResult,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        sender_display_name: str,
        sender_username: str | None,
    ) -> CreatedExpense:
        async with self._uow_factory() as uow:
            room, sender_member, _, _ = await self._room_service.ensure_room_and_member_in_uow(
                uow,
                telegram_chat_id=telegram_chat_id,
                chat_title=chat_title,
                telegram_user_id=telegram_user_id,
                display_name=sender_display_name,
                username=sender_username,
            )

            # Reuse eager-loaded room.members directly in RAM (no extra list_members query)
            member_contexts = [
                MemberContext(
                    member_id=m.id,
                    display_name=m.user.display_name,
                    username=m.user.username,
                )
                for m in room.members
            ]
            names_by_member_id = {m.member_id: m.display_name for m in member_contexts}

            parsed = self._parser.parse(
                raw,
                sender_member_id=sender_member.id,
                room_members=member_contexts,
            )

            category = await uow.rooms.get_category_by_name(room.id, parsed.category_name)
            if category is None or category.is_archived:
                category = await uow.rooms.get_category_by_name(room.id, "Other")
            if category is None:
                raise NotFoundError("Default 'Other' category missing for room")

            # BR02: Rent and utility bills mandate manual unanimous approval (no timer).
            if category.name in {"Rent", "Utilities"}:
                review_window = None
                review_deadline = None
            else:
                review_window = room.review_timeout_minutes
                review_deadline = datetime.now(UTC) + timedelta(minutes=review_window)

            expense = Expense(
                room_id=room.id,
                category_id=category.id,
                created_by_member_id=sender_member.id,
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
