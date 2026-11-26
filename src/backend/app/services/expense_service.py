"""Application service for UC01: Log Shared Expense via natural language text."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.adapters.ai_extraction import AIExtractionAdapter
from app.adapters.vnd_parser import RawExtractionResult
from app.db.enums import (
    ApprovalDecision,
    ExpenseStatus,
    LedgerEntryType,
    RejectionReason,
    SourceType,
    SplitType,
)
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
    """Summary of a newly persisted draft expense for bot card rendering."""

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
    split_type: SplitType


@dataclass(frozen=True, slots=True)
class ReviewedSplit:
    display_name: str
    share_amount: int
    decision: ApprovalDecision | None


@dataclass(frozen=True, slots=True)
class ExpenseReview:
    content_revision: int
    expense_id: uuid.UUID
    version: int
    description: str
    total_amount: int
    payer_name: str
    category_name: str
    status: ExpenseStatus
    splits: tuple[ReviewedSplit, ...]
    review_deadline: datetime | None
    agreed_count: int
    voter_count: int
    category_id: uuid.UUID
    payer_id: uuid.UUID
    shares: dict[uuid.UUID, int]
    ratios: dict[uuid.UUID, int]
    mentions: tuple[tuple[int, str], ...]
    members: dict[uuid.UUID, str]
    categories: dict[uuid.UUID, str]
    can_edit: bool
    can_cancel: bool
    can_vote: bool
    split_type: SplitType
    balances: tuple[tuple[str, int], ...]
    rejection: str | None
    payer_decision: ApprovalDecision | None


@dataclass(frozen=True, slots=True)
class ExpenseEdit:
    description: str
    total_amount: int
    category_id: uuid.UUID
    payer_id: uuid.UUID
    shares: dict[uuid.UUID, int]
    split_type: SplitType


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
        """Extract, parse, and persist a draft expense in a single DB transaction."""

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

            if parsed.payer_member_id != sender_member.id:
                raise ValidationError("Người trả phải tự tạo khoản chi.")

            category = await uow.rooms.get_category_by_name(room.id, parsed.category_name)
            if category is None or category.is_archived:
                category = await uow.rooms.get_category_by_name(room.id, "Other")
            if category is None:
                raise NotFoundError("Default 'Other' category missing for room")

            # BR02: Rent and utility bills mandate manual unanimous approval (no timer).
            if category.name in {"Rent", "Utilities"}:
                review_window = None
            else:
                review_window = room.review_timeout_minutes

            expense = Expense(
                room_id=room.id,
                category_id=category.id,
                created_by_member_id=sender_member.id,
                payer_member_id=parsed.payer_member_id,
                description=parsed.description,
                total_amount=parsed.total_amount,
                split_type=parsed.split_type,
                status=ExpenseStatus.DRAFT,
                source_type=SourceType.TEXT,
                review_window_minutes=review_window,
                review_deadline=None,
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
                split_type=parsed.split_type,
            )

    async def review(
        self,
        *,
        expense_id: uuid.UUID,
        version: int,
        action: str,
        telegram_chat_id: int,
        telegram_user_id: int,
        edit: ExpenseEdit | None = None,
        reason: RejectionReason | None = None,
        note: str | None = None,
    ) -> ExpenseReview:
        """Serialize votes on a revision and post its balanced entries on unanimity."""
        async with self._uow_factory() as uow:
            result = await self._review(
                uow,
                expense_id=expense_id,
                version=version,
                action=action,
                telegram_chat_id=telegram_chat_id,
                telegram_user_id=telegram_user_id,
                edit=edit,
                reason=reason,
                note=note,
            )
            await uow.commit()
            return result

    @asynccontextmanager
    async def publication(self, expense_id, chat_id, user_id):
        """Hold the expense row until its latest snapshot has been delivered to Telegram."""
        async with self._uow_factory() as uow:
            snapshot = await self._review(
                uow,
                expense_id=expense_id,
                version=0,
                action="refresh",
                telegram_chat_id=chat_id,
                telegram_user_id=user_id,
            )
            expense = await uow.expenses.get(expense_id, for_update=True)
            yield snapshot, expense
            await uow.commit()

    async def _review(
        self,
        uow,
        *,
        expense_id: uuid.UUID,
        version: int,
        action: str,
        telegram_chat_id: int,
        telegram_user_id: int,
        edit: ExpenseEdit | None = None,
        reason: RejectionReason | None = None,
        note: str | None = None,
    ) -> ExpenseReview:
        """Serialize votes on a revision and post its balanced entries on unanimity."""
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
        creator = actor == expense.created_by_member_id
        if actor is None:
            raise PermissionDeniedError("Bạn không thuộc phòng này.")
        if action == "refresh":
            pass
        elif action == "edit":
            if actor != expense.payer_member_id:
                raise PermissionDeniedError("Chỉ người trả được chỉnh sửa khoản chi.")
        elif action in {"cancel", "share"}:
            if not creator:
                raise PermissionDeniedError("Chỉ người tạo được thực hiện thao tác này.")
        elif actor not in involved:
            raise PermissionDeniedError("Chỉ người liên quan được thực hiện thao tác này.")
        now = datetime.now(UTC)
        if (
            expense.status == ExpenseStatus.PENDING
            and expense.review_deadline
            and expense.review_deadline <= now
        ):
            await self._resolve_due(uow, expense, room.review_default_action)
            if action != "refresh":
                await uow.commit()
                raise ConflictError("Khoản chi đã hết hạn.")
        if action != "refresh":
            permitted = {
                ExpenseStatus.DRAFT: {"edit", "share", "cancel"},
                ExpenseStatus.PENDING: {"edit", "agree", "reject", "cancel"},
                ExpenseStatus.DISPUTED: {"edit", "cancel"},
            }
            if expense.version != version or action not in permitted.get(expense.status, set()):
                raise ConflictError("Khoản chi đã thay đổi. Hãy mở phiên bản mới nhất.")
        votes = {
            a.member_id: a.decision
            for a in expense.approvals
            if a.expense_version == expense.version
        }
        status = expense.status
        changes = {}
        if action == "share":
            status = ExpenseStatus.PENDING
            if actor in involved:
                votes[actor] = ApprovalDecision.AGREE
            window = (
                room.review_timeout_minutes if expense.review_window_minutes is not None else None
            )
            changes["review_window_minutes"] = window
            changes["review_deadline"] = now + timedelta(minutes=window) if window else None
        elif action == "cancel":
            status = ExpenseStatus.CANCELLED
            changes.update(review_deadline=None, cancelled_at=now, cancelled_by_member_id=actor)
        elif action == "edit":
            if edit is not None and edit.payer_id != expense.payer_member_id:
                raise ValidationError("Không thể đổi người trả của khoản chi.")
            if edit is None or not edit.description.strip() or len(edit.description) > 500:
                raise ValidationError("Nhập mô tả từ 1 đến 500 ký tự.")
            if (
                edit.payer_id not in members
                or not edit.shares
                or not edit.shares.keys() <= members.keys()
            ):
                raise ValidationError("Người trả và người tham gia phải thuộc phòng.")
            category = await uow.rooms.get_category(edit.category_id)
            if not category or category.room_id != room.id or category.is_archived:
                raise ValidationError("Danh mục không hợp lệ.")
            shares = dict(edit.shares)
            first = (
                edit.payer_id
                if edit.payer_id in shares
                else min(shares, key=lambda k: (members[k].display_name.casefold(), k))
            )
            ratios = {}
            if edit.split_type == SplitType.EQUAL:
                share, remainder = divmod(edit.total_amount, len(shares))
                shares = dict.fromkeys(shares, share)
                shares[first] += remainder
            elif edit.split_type == SplitType.CUSTOM_RATIO:
                # The form sends hundredths of a percent to avoid binary float rounding.
                if min(shares.values()) <= 0 or sum(shares.values()) != 10_000:
                    raise ValidationError("Tổng tỷ lệ phải bằng 100%.")
                ratios = {k: Decimal(v) / 100 for k, v in shares.items()}
                shares = {k: (edit.total_amount * v + 5000) // 10000 for k, v in shares.items()}
                shares[first] += edit.total_amount - sum(shares.values())
            if min(shares.values()) <= 0 or sum(shares.values()) != edit.total_amount:
                raise ValidationError("Tổng các phần chia dương phải bằng tổng tiền.")
            window = (
                expense.review_window_minutes
                if expense.source_type == SourceType.TEXT
                and category.name not in {"Rent", "Utilities"}
                else None
            )
            changes.update(
                description=edit.description.strip(),
                category_id=category.id,
                total_amount=edit.total_amount,
                split_type=edit.split_type,
            )
            await uow.expenses.replace_splits(
                expense,
                [
                    ExpenseSplit(member_id=k, share_amount=v, share_ratio=ratios.get(k))
                    for k, v in shares.items()
                ],
            )
            await uow.expenses.clear_approvals(expense_id)
            votes.clear()
            involved = {edit.payer_id, *shares}
            if status != ExpenseStatus.DRAFT:
                changes["content_revision"] = expense.content_revision + 1
                status = ExpenseStatus.PENDING
                changes["review_deadline"] = now + timedelta(minutes=window) if window else None
                if actor in involved:
                    votes[actor] = ApprovalDecision.AGREE
        elif action in ("agree", "reject"):
            if action == "reject":
                if reason is None or (reason == RejectionReason.OTHER and not (note or "").strip()):
                    raise ValidationError("Chọn lý do từ chối và giải thích nếu chọn lý do khác.")
                status = ExpenseStatus.DISPUTED
                changes["review_deadline"] = None
            votes[actor] = ApprovalDecision(action.upper())
        if action != "refresh":
            if status == ExpenseStatus.PENDING and all(
                votes.get(m) == ApprovalDecision.AGREE for m in involved
            ):
                status = ExpenseStatus.CONFIRMED
                changes.update(confirmed_at=now, review_deadline=None)
            target_version = version
            if changes or status != expense.status:
                if not await uow.expenses.update_if_version(
                    expense_id,
                    version,
                    expected_statuses=[expense.status],
                    status=status,
                    **changes,
                ):
                    raise ConflictError("This expense has changed.")
                if action == "edit":
                    # Use the saved revision for both ledger posting and the Telegram card.
                    expense = await uow.expenses.get(expense_id)
                    if expense is None:
                        raise NotFoundError("Expense unavailable in this chat.")
                target_version = version + 1
                if action != "edit":
                    # A status transition carries existing votes on the same content forward.
                    for approval in expense.approvals:
                        if (
                            action == "cancel" or approval.member_id != actor
                        ) and approval.expense_version == version:
                            approval.expense_version = target_version
            if actor in votes and action != "cancel":
                await uow.expenses.upsert_approval(
                    expense_id=expense_id,
                    member_id=actor,
                    decision=votes[actor],
                    expense_version=target_version,
                    reason_code=reason,
                    reason_note=note if reason == RejectionReason.OTHER else None,
                )
            if status == ExpenseStatus.CONFIRMED:
                await self._post_ledger(uow, expense, now)
        await uow.flush()
        expense = await uow.expenses.get(expense_id)
        category = await uow.rooms.get_category(expense.category_id)
        names = {member_id: user.display_name for member_id, user in members.items()}
        balances = (
            await uow.ledger.net_balances(room.id) if status == ExpenseStatus.CONFIRMED else {}
        )
        rejection = next(
            (a for a in expense.approvals if a.decision == ApprovalDecision.REJECT), None
        )
        reason_labels = {
            "WRONG_AMOUNT": "Sai số tiền",
            "WRONG_PARTICIPANTS": "Sai thành viên",
            "NOT_MY_EXPENSE": "Không tham gia",
            "DUPLICATE": "Trùng khoản chi",
            "OTHER": "Lý do khác",
        }
        reason_label = reason_labels.get(rejection.reason_code, "") if rejection else ""
        review = ExpenseReview(
            content_revision=expense.content_revision,
            expense_id=expense_id,
            version=expense.version,
            description=expense.description,
            status=status,
            category_id=expense.category_id,
            payer_id=expense.payer_member_id,
            shares={sp.member_id: sp.share_amount for sp in expense.splits},
            members=names,
            ratios={
                sp.member_id: int(sp.share_ratio * 100) for sp in expense.splits if sp.share_ratio
            },
            mentions=tuple(
                (members[k].telegram_user_id, members[k].display_name)
                for k in sorted(involved | {expense.created_by_member_id})
                if k in members
            ),
            categories={c.id: c.name for c in await uow.rooms.list_categories(room.id)},
            can_edit=actor == expense.payer_member_id
            and status in {ExpenseStatus.DRAFT, ExpenseStatus.PENDING, ExpenseStatus.DISPUTED},
            can_vote=status == ExpenseStatus.PENDING and actor in involved,
            can_cancel=creator
            and status in {ExpenseStatus.PENDING, ExpenseStatus.DISPUTED, ExpenseStatus.DRAFT},
            split_type=expense.split_type,
            balances=tuple(
                (names.get(k, "Thành viên"), balances.get(k, 0)) for k in sorted(involved)
            )
            if status == ExpenseStatus.CONFIRMED
            else (),
            rejection=(
                f"{names.get(rejection.member_id, 'Thành viên')}: "
                f"{reason_label} {rejection.reason_note or ''}".strip()
            )
            if rejection
            else None,
            total_amount=expense.total_amount,
            category_name=category.name,
            payer_name=names.get(expense.payer_member_id, "Thành viên"),
            review_deadline=expense.review_deadline,
            splits=tuple(
                ReviewedSplit(
                    names.get(s.member_id, "Thành viên"),
                    s.share_amount,
                    votes.get(s.member_id),
                )
                for s in expense.splits
            ),
            agreed_count=sum(v == ApprovalDecision.AGREE for v in votes.values()),
            voter_count=len(involved),
            payer_decision=votes.get(expense.payer_member_id),
        )
        return review

    @staticmethod
    async def _post_ledger(uow, expense, now):
        expense_id = expense.id
        deltas = {s.member_id: -s.share_amount for s in expense.splits}
        payer = expense.payer_member_id
        deltas[payer] = deltas.get(payer, 0) + expense.total_amount
        if sum(deltas.values()):
            raise ValidationError("Split amounts must add up to the total.")
        await uow.ledger.append_many(
            LedgerEntry(
                room_id=expense.room_id,
                member_id=member,
                expense_id=expense_id,
                entry_type=LedgerEntryType.EXPENSE,
                amount_delta=delta,
                effective_at=now,
            )
            for member, delta in deltas.items()
            if delta
        )

    async def _resolve_due(self, uow, expense, default_action):
        deadline = expense.review_deadline
        confirm = default_action.value == "CONFIRM"
        status = ExpenseStatus.CONFIRMED if confirm else ExpenseStatus.CANCELLED
        old_version = expense.version
        if await uow.expenses.update_if_version(
            expense.id,
            old_version,
            expected_statuses=[ExpenseStatus.PENDING],
            status=status,
            auto_resolved=True,
            confirmed_at=deadline if confirm else None,
            cancelled_at=None if confirm else deadline,
            review_deadline=None,
        ):
            for approval in expense.approvals:
                if approval.expense_version == old_version:
                    approval.expense_version = old_version + 1
            if confirm:
                await self._post_ledger(uow, expense, deadline)

    async def bind_card(self, expense_id, message_id):
        async with self._uow_factory() as uow:
            expense = await uow.expenses.get(expense_id, for_update=True)
            if expense and not expense.card_message_id:
                expense.card_message_id = message_id
                await uow.commit()

    async def resolve_room(self, chat_id, *, user_id=None):
        """Recheck candidates under their row lock, committing before notifying Telegram."""
        async with self._uow_factory() as uow:
            room = await uow.rooms.get_room_by_chat_id(chat_id)
            if not room:
                return []
            if user_id is not None and all(
                member.user.telegram_user_id != user_id for member in room.members
            ):
                raise PermissionDeniedError("Bạn không thuộc phòng này.")
            now = datetime.now(UTC)
            candidates = await uow.expenses.list_overdue(room.id, now)
            users = {m.id: m.user.telegram_user_id for m in room.members}
            resolved = []
            for candidate in sorted(candidates, key=lambda row: row.id):
                expense = await uow.expenses.get(candidate.id, for_update=True)
                if (
                    expense
                    and expense.status == ExpenseStatus.PENDING
                    and expense.review_deadline
                    and expense.review_deadline <= now
                ):
                    await self._resolve_due(uow, expense, room.review_default_action)
                    resolved.append((expense.id, users[expense.created_by_member_id]))
            await uow.commit()
            return resolved
