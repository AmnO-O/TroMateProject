from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.expense_model import Expense


class ExpenseSplit(UUIDPrimaryKeyMixin, Base):
    """One participant's share of an expense (``expense_shares`` in the SCRUM-117 ERD)."""

    __tablename__ = "expense_splits"
    __table_args__ = (
        UniqueConstraint("expense_id", "member_id"),
        # BR05: every participant's share must be greater than zero.
        CheckConstraint("share_amount > 0", name="share_amount_positive"),
        CheckConstraint("share_ratio IS NULL OR share_ratio > 0", name="share_ratio_positive"),
    )

    expense_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("expenses.id", ondelete="CASCADE"))
    member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("room_members.id", ondelete="RESTRICT"), index=True
    )
    share_amount: Mapped[int] = mapped_column(BigInteger)  # whole VND
    # Percentage or weight entered for CUSTOM_RATIO splits.
    share_ratio: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))

    expense: Mapped[Expense] = relationship(back_populates="splits", lazy="raise")
