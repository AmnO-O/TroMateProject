"""Application service for UC01: Log Shared Expense via natural language text."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

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
from app.db.models import Expense, ExpenseApproval, ExpenseSplit, LedgerEntry, Room
from app.db.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.services.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.services.expense_parser import ExpenseParser, MemberContext
from app.services.room_service import RoomService

REASON_LABELS = {
    "WRONG_AMOUNT": "Sai số tiền",
    "WRONG_PARTICIPANTS": "Sai thành viên",
    "NOT_MY_EXPENSE": "Không tham gia",
    "DUPLICATE": "Trùng khoản chi",
    "OTHER": "Lý do khác",
}

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
    last_change: str
    can_add_reason: bool
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
        card_message_id: int | None = None,
        now: datetime | None = None,
    ) -> CreatedExpense:
        """Persist a prepared draft as ``PENDING``, latching the room window at share time."""

        async with self._uow_factory() as uow:
            room = await uow.rooms.get_room(draft.room_id)
            if room is None:
                raise NotFoundError("Room not found")
            created = await self._persist_draft_in_uow(
                uow, room, draft, now=now, card_message_id=card_message_id
            )
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
        card_message_id: int | None = None,
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
            card_message_id=card_message_id,
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
        if card_message_id is not None:
            uow.expenses.enqueue(expense)

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

    async def queue_refresh(self, expense_id, chat_id, user_id, fallback):
        async with self._uow_factory() as uow:
            await self._review(
                uow,
                expense_id=expense_id,
                version=0,
                action="refresh",
                telegram_chat_id=chat_id,
                telegram_user_id=user_id,
            )
            expense = await uow.expenses.get(expense_id, for_update=True)
            if expense.card_message_id is None:
                expense.card_message_id = fallback
            uow.expenses.enqueue(expense)
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
        if action != "refresh" and expense.version != version:
            raise ConflictError("Khoản chi đã thay đổi. Hãy mở phiên bản mới nhất.")
        if action == "refresh":
            pass
        elif action == "edit":
            if not creator:
                raise PermissionDeniedError("Chỉ người trả được chỉnh sửa khoản chi.")
        elif action == "cancel":
            if not creator:
                raise PermissionDeniedError("Chỉ người tạo được thực hiện thao tác này.")
        elif creator or actor not in involved:
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
                ExpenseStatus.PENDING: {"edit", "agree", "reject", "cancel"},
                ExpenseStatus.DISPUTED: {"edit", "cancel", "addreason"},
            }
            if action not in permitted.get(expense.status, set()):
                raise ConflictError("Khoản chi đã thay đổi. Hãy mở phiên bản mới nhất.")
        votes = {
            a.member_id: a.decision
            for a in expense.approvals
            if a.expense_version == expense.version
        }
        status = expense.status
        changes = {}
        if action == "cancel":
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
            labels = [
                label
                for old, new, label in (
                    (expense.description, edit.description.strip(), "mô tả"),
                    (expense.total_amount, edit.total_amount, "tổng tiền"),
                    (expense.category_id, category.id, "danh mục"),
                    (expense.split_type, edit.split_type, "cách chia"),
                    (
                        {sp.member_id: (sp.share_amount, sp.share_ratio) for sp in expense.splits},
                        {k: (v, ratios.get(k)) for k, v in shares.items()},
                        "phần chia",
                    ),
                )
                if old != new
            ]
            changes["last_change"] = f"Phiên bản {expense.content_revision + 1}: " + (
                ", ".join(labels) or "đã lưu lại"
            )
            changes["dispute_reasons"] = []
            previous = {sp.member_id for sp in expense.splits}
            for key in previous.symmetric_difference(shares):
                if key in members:
                    change = "được thêm vào" if key in shares else "được bỏ khỏi"
                    uow.expenses.enqueue(
                        expense,
                        "notice",
                        recipient=members[key].telegram_user_id,
                        body=f"Bạn {change} khoản chi {edit.description}.",
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
        elif action in ("agree", "reject", "addreason"):
            if action in {"reject", "addreason"}:
                if reason is None or (reason == RejectionReason.OTHER and not (note or "").strip()):
                    raise ValidationError("Chọn lý do từ chối và giải thích nếu chọn lý do khác.")
                status = ExpenseStatus.DISPUTED
                changes["review_deadline"] = None
                reason_text = f"{members[actor].display_name}: {REASON_LABELS[reason]}"
                if reason == RejectionReason.OTHER:
                    reason_text += f" · {note.strip()}"
                history = list(expense.dispute_reasons or [])
                if not history and action == "addreason":
                    for approval in expense.approvals:
                        if approval.decision == ApprovalDecision.REJECT:
                            user = members.get(approval.member_id)
                            label = REASON_LABELS.get(approval.reason_code, "")
                            history.append(
                                f"{user.display_name if user else 'Thành viên'}: "
                                f"{label} {approval.reason_note or ''}".rstrip()
                            )
                changes["dispute_reasons"] = [*history, reason_text]
                uow.expenses.enqueue(
                    expense,
                    "notice",
                    body=f"{expense.description} · {reason_text}",
                )
                if action == "reject":
                    uow.expenses.enqueue(expense, "reminder", available_at=now + timedelta(days=3))
            if action != "addreason":
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
                            action in {"cancel", "addreason"} or approval.member_id != actor
                        ) and approval.expense_version == version:
                            approval.expense_version = target_version
            if actor in votes and action not in {"cancel", "addreason"}:
                await uow.expenses.upsert_approval(
                    expense_id=expense_id,
                    member_id=actor,
                    decision=votes[actor],
                    expense_version=target_version,
                    reason_code=reason,
                    reason_note=note if reason == RejectionReason.OTHER else None,
                )
            uow.expenses.enqueue(expense)
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
        reason_label = REASON_LABELS.get(rejection.reason_code, "") if rejection else ""
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
            can_edit=creator
            and status in {ExpenseStatus.DRAFT, ExpenseStatus.PENDING, ExpenseStatus.DISPUTED},
            last_change=expense.last_change,
            can_add_reason=status == ExpenseStatus.DISPUTED and not creator and actor in involved,
            can_vote=status == ExpenseStatus.PENDING and not creator and actor in involved,
            can_cancel=creator
            and status in {ExpenseStatus.PENDING, ExpenseStatus.DISPUTED, ExpenseStatus.DRAFT},
            split_type=expense.split_type,
            balances=tuple(
                (names.get(k, "Thành viên"), balances.get(k, 0)) for k in sorted(involved)
            )
            if status == ExpenseStatus.CONFIRMED
            else (),
            rejection="\n".join(expense.dispute_reasons or [])
            or (
                (
                    f"{names.get(rejection.member_id, 'Thành viên')}: "
                    f"{reason_label} {rejection.reason_note or ''}".strip()
                )
                if rejection
                else None
            ),
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
            uow.expenses.enqueue(expense)
            if confirm:
                await self._post_ledger(uow, expense, deadline)

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

    async def deliver_next(self, deliver):
        """Claim one due job. A failed send is retried independently of expense transitions."""
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            job = await uow.expenses.next_delivery(now)
            if job is None:
                return False
            expense = await uow.expenses.get(job.expense_id, for_update=True)
            room = await uow.rooms.get_room(expense.room_id)
            creator = next(
                m.user.telegram_user_id
                for m in room.members
                if m.id == expense.created_by_member_id
            )
            active_reminder = (
                job.kind == "reminder"
                and expense.status == ExpenseStatus.DISPUTED
                and expense.content_revision == job.revision
            )
            if job.kind != "reminder" or active_reminder:
                review = await self._review(
                    uow,
                    expense_id=expense.id,
                    version=expense.version,
                    action="refresh",
                    telegram_chat_id=room.telegram_chat_id,
                    telegram_user_id=creator,
                )
                try:
                    retired = await deliver(job, expense, review, room.telegram_chat_id, creator)
                except Exception as exc:
                    import logging

                    logging.getLogger(__name__).warning(
                        "Expense delivery %s failed (%s)", job.id, type(exc).__name__
                    )
                    job.attempts += 1
                    delay = max(
                        getattr(exc, "retry_after", 0), min(3600, 5 * 2 ** min(job.attempts, 10))
                    )
                    job.available_at = now + timedelta(seconds=delay)
                    await uow.commit()
                    return True
                if retired:
                    uow.expenses.enqueue(expense, "retire", recipient=retired)
            if active_reminder:
                job.available_at = now + timedelta(days=3)
                job.attempts = 0
            else:
                await uow.expenses.finish_delivery(job)
            await uow.commit()
            return True
