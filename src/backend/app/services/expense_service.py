"""Application service for UC01: Log Shared Expense via natural language text."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy.exc import IntegrityError

from app.adapters.ai_extraction import AIExtractionAdapter
from app.adapters.vnd_parser import RawExtractionResult
from app.db.enums import ApprovalDecision, ExpenseStatus, SourceType, SplitType
from app.db.models import Expense, ExpenseApproval, ExpenseSplit, Room
from app.db.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.services.errors import NotFoundError
from app.services.expense_parser import ExpenseParser, MemberContext
from app.services.room_service import RoomService

MANUAL_ONLY_CATEGORIES: frozenset[str] = frozenset({"Rent", "Utilities"})
ManualReason = Literal["MANUAL_CATEGORY", "NO_ROOM_WINDOW", "CREATOR_DISABLED", "NON_TEXT"]


def resolve_auto_confirm_window(
    *,
    source_type: SourceType,
    category_name: str,
    room_window_minutes: int | None,
    auto_confirm_enabled: bool,
    now: datetime | None = None,
) -> tuple[int | None, datetime | None]:
    """Resolve effective auto-confirm window and deadline at share time (BR02, BR03)."""

    if (
        source_type != SourceType.TEXT
        or category_name in MANUAL_ONLY_CATEGORIES
        or room_window_minutes is None
        or not auto_confirm_enabled
    ):
        return None, None
    effective_now = now or datetime.now(UTC)
    return room_window_minutes, effective_now + timedelta(minutes=room_window_minutes)


@dataclass(frozen=True, slots=True)
class CreatedSplitLine:
    member_id: uuid.UUID
    display_name: str
    share_amount: int


@dataclass(frozen=True, slots=True)
class ExpenseDraft:
    """In-memory UC01 v3.0 draft summary prepared before the creator clicks Share."""

    draft_id: uuid.UUID
    room_id: uuid.UUID
    telegram_chat_id: int
    chat_title: str
    creator_telegram_user_id: int
    creator_member_id: uuid.UUID
    creator_display_name: str
    creator_username: str | None
    description: str
    total_amount: int
    payer_member_id: uuid.UUID
    payer_name: str
    category_id: uuid.UUID
    category_name: str
    split_type: SplitType
    splits: tuple[CreatedSplitLine, ...]
    source_type: SourceType
    room_window_minutes: int | None
    auto_confirm_eligible: bool
    auto_confirm_enabled: bool
    manual_reason: ManualReason | None
    extraction_source: str

    def with_auto_confirm_disabled(self) -> ExpenseDraft:
        """Return a copy with auto-confirm disabled while preserving non-creator reasons."""

        return replace(
            self,
            auto_confirm_enabled=False,
            manual_reason=(
                "CREATOR_DISABLED" if self.manual_reason is None else self.manual_reason
            ),
        )


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
    review_window_minutes: int | None = None


class ExpenseService:
    """Orchestrates extraction -> parsing -> draft summary -> PostgreSQL persistence for UC01."""

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

    async def prepare_expense_draft(
        self,
        *,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        sender_display_name: str,
        sender_username: str | None,
        text: str,
        source_type: SourceType = SourceType.TEXT,
    ) -> ExpenseDraft | None:
        """Extract and parse a draft summary without inserting any ``Expense`` row."""

        raw = await self._extractor.extract(text)
        if raw is None:
            return None

        async def _once() -> ExpenseDraft:
            async with self._uow_factory() as uow:
                _, draft = await self._prepare_draft_in_uow(
                    uow,
                    raw=raw,
                    telegram_chat_id=telegram_chat_id,
                    chat_title=chat_title,
                    telegram_user_id=telegram_user_id,
                    sender_display_name=sender_display_name,
                    sender_username=sender_username,
                    source_type=source_type,
                )
                await uow.commit()
                return draft

        try:
            return await _once()
        except IntegrityError:
            return await _once()

    async def share_expense_draft(
        self,
        draft: ExpenseDraft,
        *,
        now: datetime | None = None,
    ) -> CreatedExpense:
        """Persist a prepared draft as ``PENDING``, latching the room window at share time."""

        async with self._uow_factory() as uow:
            room = await uow.rooms.get_room(draft.room_id)
            if room is None:
                raise NotFoundError("Room not found")
            created = await self._persist_draft_in_uow(uow, room, draft, now=now)
            await uow.commit()
            return created

    async def log_expense_from_text(
        self,
        *,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        sender_display_name: str,
        sender_username: str | None,
        text: str,
        auto_confirm: bool = True,
        source_type: SourceType = SourceType.TEXT,
        now: datetime | None = None,
    ) -> CreatedExpense | None:
        """Extract, parse, and persist a ``PENDING`` expense in a single DB transaction."""

        raw = await self._extractor.extract(text)
        if raw is None:
            return None

        async def _once() -> CreatedExpense:
            async with self._uow_factory() as uow:
                room, draft = await self._prepare_draft_in_uow(
                    uow,
                    raw=raw,
                    telegram_chat_id=telegram_chat_id,
                    chat_title=chat_title,
                    telegram_user_id=telegram_user_id,
                    sender_display_name=sender_display_name,
                    sender_username=sender_username,
                    source_type=source_type,
                )
                if not auto_confirm:
                    draft = draft.with_auto_confirm_disabled()
                created = await self._persist_draft_in_uow(uow, room, draft, now=now)
                await uow.commit()
                return created

        try:
            return await _once()
        except IntegrityError:
            return await _once()

    async def _prepare_draft_in_uow(
        self,
        uow: UnitOfWork,
        *,
        raw: RawExtractionResult,
        telegram_chat_id: int,
        chat_title: str,
        telegram_user_id: int,
        sender_display_name: str,
        sender_username: str | None,
        source_type: SourceType,
    ) -> tuple[Room, ExpenseDraft]:
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

        manual_reason: ManualReason | None
        if source_type != SourceType.TEXT:
            eligible, enabled, manual_reason = False, False, "NON_TEXT"
        elif category.name in MANUAL_ONLY_CATEGORIES:
            eligible, enabled, manual_reason = False, False, "MANUAL_CATEGORY"
        elif room.review_timeout_minutes is None:
            eligible, enabled, manual_reason = False, False, "NO_ROOM_WINDOW"
        else:
            eligible, enabled, manual_reason = True, True, None

        draft = ExpenseDraft(
            draft_id=uuid.uuid4(),
            room_id=room.id,
            telegram_chat_id=telegram_chat_id,
            chat_title=chat_title,
            creator_telegram_user_id=telegram_user_id,
            creator_member_id=sender_member.id,
            creator_display_name=sender_display_name,
            creator_username=sender_username,
            description=parsed.description,
            total_amount=parsed.total_amount,
            payer_member_id=parsed.payer_member_id,
            payer_name=names_by_member_id.get(parsed.payer_member_id, sender_display_name),
            category_id=category.id,
            category_name=category.name,
            split_type=parsed.split_type,
            splits=tuple(
                CreatedSplitLine(
                    member_id=split.member_id,
                    display_name=names_by_member_id.get(split.member_id, "Member"),
                    share_amount=split.share_amount,
                )
                for split in parsed.splits
            ),
            source_type=source_type,
            room_window_minutes=room.review_timeout_minutes,
            auto_confirm_eligible=eligible,
            auto_confirm_enabled=enabled,
            manual_reason=manual_reason,
            extraction_source=raw.source,
        )
        return room, draft

    async def _persist_draft_in_uow(
        self,
        uow: UnitOfWork,
        room: Room,
        draft: ExpenseDraft,
        *,
        now: datetime | None = None,
    ) -> CreatedExpense:
        # BR03: latch room.review_timeout_minutes at share time so later room changes don't mutate
        # already-shared expenses.
        review_window, review_deadline = resolve_auto_confirm_window(
            source_type=draft.source_type,
            category_name=draft.category_name,
            room_window_minutes=room.review_timeout_minutes,
            auto_confirm_enabled=draft.auto_confirm_enabled,
            now=now,
        )

        expense = Expense(
            room_id=room.id,
            category_id=draft.category_id,
            created_by_member_id=draft.creator_member_id,
            payer_member_id=draft.creator_member_id,
            description=draft.description,
            total_amount=draft.total_amount,
            split_type=draft.split_type,
            status=ExpenseStatus.PENDING,
            source_type=draft.source_type,
            review_window_minutes=review_window,
            review_deadline=review_deadline,
            splits=[
                ExpenseSplit(
                    member_id=split.member_id,
                    share_amount=split.share_amount,
                )
                for split in draft.splits
            ],
            # BR01: creator's agreement is recorded when the expense is shared.
            approvals=[
                ExpenseApproval(
                    member_id=draft.creator_member_id,
                    decision=ApprovalDecision.AGREE,
                    expense_version=1,
                )
            ],
        )
        await uow.expenses.add(expense)

        return CreatedExpense(
            expense_id=expense.id,
            version=expense.version,
            description=expense.description,
            total_amount=expense.total_amount,
            payer_name=draft.creator_display_name,
            category_name=draft.category_name,
            status=expense.status,
            splits=draft.splits,
            review_deadline=expense.review_deadline,
            extraction_source=draft.extraction_source,
            review_window_minutes=expense.review_window_minutes,
        )
