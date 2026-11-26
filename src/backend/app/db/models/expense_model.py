from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Text, false, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, str_enum
from app.db.enums import ExpenseStatus, SourceType, SplitType

if TYPE_CHECKING:
    from app.db.models.expense_approval_model import ExpenseApproval
    from app.db.models.expense_split_model import ExpenseSplit


class Expense(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A shared expense and its confirmation state (see ``ExpenseStatus``).

    ``version`` is the optimistic-locking counter: every state change or edit goes through
    ``ExpenseRepository.update_if_version`` (``UPDATE ... WHERE id = :id AND version = :v``),
    so a stale vote or edit updates zero rows and the service answers 409 Conflict.
    """

    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("total_amount > 0", name="total_amount_positive"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "review_window_minutes IS NULL OR review_window_minutes > 0",
            name="review_window_positive",
        ),
        CheckConstraint(
            "(status = 'CONFIRMED') = (confirmed_at IS NOT NULL)",
            name="confirmed_at_matches_status",
        ),
        # Lazy resolve_overdue(room): PENDING expenses whose review_deadline has passed.
        Index("ix_expenses_room_id_status_review_deadline", "room_id", "status", "review_deadline"),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    created_by_member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("room_members.id", ondelete="RESTRICT")
    )
    payer_member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("room_members.id", ondelete="RESTRICT")
    )
    dispute_reasons: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'")
    )
    last_change: Mapped[str] = mapped_column(Text, default="", server_default=text("''"))
    card_revision: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    card_message_id: Mapped[int | None] = mapped_column(BigInteger)
    description: Mapped[str] = mapped_column(Text)
    total_amount: Mapped[int] = mapped_column(BigInteger)  # whole VND
    split_type: Mapped[SplitType] = mapped_column(str_enum(SplitType, length=20))
    status: Mapped[ExpenseStatus] = mapped_column(
        str_enum(ExpenseStatus), server_default=text("'PENDING'"), default=ExpenseStatus.PENDING
    )
    source_type: Mapped[SourceType] = mapped_column(str_enum(SourceType))
    receipt_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="SET NULL")
    )
    # NULL while PENDING means manual approval only (BR02: photo, meter and rent expenses).
    review_deadline: Mapped[datetime | None]
    # Room window (minutes) used to compute review_deadline for this version (UC06).
    review_window_minutes: Mapped[int | None]
    # True when the room's default action resolved the expense at its deadline (UC06).
    auto_resolved: Mapped[bool] = mapped_column(server_default=false(), default=False)
    content_revision: Mapped[int] = mapped_column(server_default=text("1"), default=1)
    version: Mapped[int] = mapped_column(server_default=text("1"), default=1)
    confirmed_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    cancelled_by_member_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("room_members.id", ondelete="RESTRICT")
    )

    splits: Mapped[list[ExpenseSplit]] = relationship(
        back_populates="expense",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    approvals: Mapped[list[ExpenseApproval]] = relationship(
        back_populates="expense",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ExpenseDelivery(UUIDPrimaryKeyMixin, Base):
    """Durable Telegram work queued in the transaction that changes an expense."""

    __tablename__ = "expense_deliveries"

    expense_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"))
    revision: Mapped[int]
    kind: Mapped[str]
    recipient: Mapped[int | None] = mapped_column(BigInteger)
    body: Mapped[str] = mapped_column(Text)
    available_at: Mapped[datetime] = mapped_column(index=True, server_default=func.now())
    attempts: Mapped[int] = mapped_column(default=0, server_default=text("0"))
