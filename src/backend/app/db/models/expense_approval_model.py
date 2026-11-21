from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, str_enum
from app.db.enums import ApprovalDecision, RejectionReason

if TYPE_CHECKING:
    from app.db.models.expense_model import Expense


class ExpenseApproval(UUIDPrimaryKeyMixin, Base):
    """A member's Agree/Reject on an expense (``expense_votes`` in the SCRUM-117 ERD).

    ``expense_version`` records which version was reviewed, so an approval given before an
    edit can never count towards the new version (UC05-AF03).
    """

    __tablename__ = "expense_approvals"
    __table_args__ = (
        UniqueConstraint("expense_id", "member_id"),
        CheckConstraint("expense_version >= 1", name="expense_version_positive"),
        CheckConstraint(
            "decision = 'REJECT' OR (reason_code IS NULL AND reason_note IS NULL)",
            name="reason_only_on_reject",
        ),
    )

    expense_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"))
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("room_members.id", ondelete="CASCADE"))
    decision: Mapped[ApprovalDecision] = mapped_column(str_enum(ApprovalDecision))
    expense_version: Mapped[int]
    # UC05-AF02: reason given when rejecting.
    reason_code: Mapped[RejectionReason | None] = mapped_column(
        str_enum(RejectionReason, length=32)
    )
    reason_note: Mapped[str | None] = mapped_column(Text)
    voted_at: Mapped[datetime] = mapped_column(server_default=func.now())

    expense: Mapped[Expense] = relationship(back_populates="approvals", lazy="raise")
