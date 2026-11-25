"""Application service for UC01: Log Shared Expense via natural language text."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.adapters.ai_extraction import AIExtractionAdapter
from app.adapters.vnd_parser import RawExtractionResult
from app.bots.interface import ConfirmationCardDTO, SplitLineDTO
from app.db.enums import ApprovalDecision, ExpenseStatus, LedgerEntryType, SourceType
from app.db.models import Expense, ExpenseSplit, LedgerEntry
from app.db.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.services.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
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

    async def review(
        self,
        *,
        expense_id: uuid.UUID,
        version: int,
        action: str,
        telegram_chat_id: int,
        telegram_user_id: int,
        description: str | None = None,
    ) -> ConfirmationCardDTO:
        """Serialize votes on a revision and post its balanced entries on unanimity."""
        replacement = None
        if action == "edit" and description and description.startswith("Expense:"):
            replacement = await self._extractor.extract(
                description.removeprefix("Expense:").strip()
            )
            if replacement is None:
                raise ValidationError("Include the amount and split in the replacement expense.")
        async with self._uow_factory() as uow:
            expense = await uow.expenses.get(expense_id, for_update=True)
            room = await uow.rooms.get_room_by_chat_id(telegram_chat_id)
            if expense is None or room is None or expense.room_id != room.id:
                raise NotFoundError("Expense unavailable in this chat.")
            members = {m.id: m.user for m in room.members}
            actor = next(
                (key for key, user in members.items() if user.telegram_user_id == telegram_user_id),
                None,
            )
            involved = {expense.payer_member_id, *(s.member_id for s in expense.splits)}
            creator_edit = action == "edit" and actor == expense.created_by_member_id
            if actor not in involved and not creator_edit:
                raise PermissionDeniedError("Only involved members may review this expense.")
            if (
                expense.status == ExpenseStatus.DISPUTED
                and not creator_edit
                and action != "refresh"
            ):
                raise ConflictError("Only the creator can edit a disputed expense.")
            if action != "refresh" and (
                expense.version != version
                or expense.status
                in (
                    ExpenseStatus.CONFIRMED,
                    ExpenseStatus.CANCELLED,
                )
            ):
                raise ConflictError("This expense has changed. Use the latest card.")

            votes = {
                a.member_id: a.decision
                for a in expense.approvals
                if a.expense_version == expense.version or expense.status != ExpenseStatus.PENDING
            }
            status = expense.status
            changes = {}
            now = datetime.now(UTC)
            if action == "edit":
                if description is not None:
                    description = description.strip()
                    if not description or len(description) > 500:
                        raise ValidationError("Enter a description of 1 to 500 characters.")
                    window = expense.review_window_minutes
                    if replacement is not None:
                        parsed = self._parser.parse(
                            replacement,
                            sender_member_id=actor,
                            room_members=[
                                MemberContext(key, user.display_name, user.username)
                                for key, user in members.items()
                            ],
                        )
                        category = await uow.rooms.get_category_by_name(
                            room.id, parsed.category_name
                        )
                        if category is None or category.is_archived:
                            category = await uow.rooms.get_category_by_name(room.id, "Other")
                        if category is None:
                            raise NotFoundError("Default category missing.")
                        window = (
                            room.review_timeout_minutes
                            if expense.source_type == SourceType.TEXT
                            and category.name not in {"Rent", "Utilities"}
                            else None
                        )
                        changes.update(
                            total_amount=parsed.total_amount,
                            category_id=category.id,
                            payer_member_id=parsed.payer_member_id,
                            split_type=parsed.split_type,
                            review_window_minutes=window,
                        )
                        await uow.expenses.replace_splits(
                            expense,
                            [
                                ExpenseSplit(member_id=s.member_id, share_amount=s.share_amount)
                                for s in parsed.splits
                            ],
                        )
                        involved = {parsed.payer_member_id, *(s.member_id for s in parsed.splits)}
                        description = parsed.description
                    changes["description"] = description
                    changes["review_deadline"] = now + timedelta(minutes=window) if window else None
                    status = ExpenseStatus.PENDING
                    await uow.expenses.clear_approvals(expense_id)
                    votes.clear()
                    if actor in involved:
                        votes[actor] = ApprovalDecision.AGREE
            elif action in ("agree", "reject"):
                votes[actor] = ApprovalDecision(action.upper())
                if action == "reject":
                    status = ExpenseStatus.DISPUTED
                    changes["review_deadline"] = None
            elif action != "refresh":
                raise ValidationError("Unknown expense action.")

            if action in ("agree", "reject") or (action == "edit" and description is not None):
                if all(votes.get(member) == ApprovalDecision.AGREE for member in involved):
                    status = ExpenseStatus.CONFIRMED
                    changes["confirmed_at"] = now
                    changes["review_deadline"] = None
                if changes or status != expense.status:
                    if not await uow.expenses.update_if_version(
                        expense_id,
                        version,
                        expected_statuses=[expense.status],
                        status=status,
                        **changes,
                    ):
                        raise ConflictError("This expense has changed.")
                if actor in votes:
                    await uow.expenses.upsert_approval(
                        expense_id=expense_id,
                        member_id=actor,
                        decision=votes[actor],
                        expense_version=expense.version if action == "edit" else version,
                    )
                if status == ExpenseStatus.CONFIRMED:
                    deltas = {s.member_id: -s.share_amount for s in expense.splits}
                    payer = expense.payer_member_id
                    deltas[payer] = deltas.get(payer, 0) + expense.total_amount
                    if sum(deltas.values()):
                        raise ValidationError("Split amounts must add up to the total.")
                    await uow.ledger.append_many(
                        LedgerEntry(
                            room_id=room.id,
                            member_id=member,
                            expense_id=expense_id,
                            entry_type=LedgerEntryType.EXPENSE,
                            amount_delta=delta,
                            effective_at=now,
                        )
                        for member, delta in deltas.items()
                        if delta
                    )
            category = await uow.rooms.get_category(expense.category_id)
            card = ConfirmationCardDTO(
                expense_id=expense_id,
                version=expense.version,
                description=expense.description,
                status=status.value,
                total_amount=expense.total_amount,
                category_name=category.name,
                payer_name=members[expense.payer_member_id].display_name,
                review_deadline=expense.review_deadline,
                splits=tuple(
                    SplitLineDTO(
                        members[s.member_id].display_name,
                        s.share_amount,
                        votes.get(s.member_id, "PENDING"),
                    )
                    for s in expense.splits
                ),
                agreed_count=sum(v == ApprovalDecision.AGREE for v in votes.values()),
                voter_count=len(involved),
                payer_decision=votes.get(expense.payer_member_id, "PENDING"),
            )
            await uow.commit()
            return card
