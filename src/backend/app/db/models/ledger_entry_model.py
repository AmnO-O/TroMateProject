from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, str_enum
from app.db.enums import LedgerEntryType


class LedgerEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable balance change. Append-only: ``LedgerRepository`` never updates or deletes.

    ``amount_delta`` is signed whole VND: ``+`` the room owes the member, ``-`` the member
    owes the room. Corrections are recorded as compensating entries.
    ``effective_at`` is when the change counts (the review deadline for an auto-resolved
    expense); ``created_at`` is when the row was written.
    """

    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount_delta <> 0", name="amount_delta_non_zero"),
        CheckConstraint(
            "(entry_type = 'EXPENSE' AND expense_id IS NOT NULL AND payment_id IS NULL)"
            " OR (entry_type = 'SETTLEMENT' AND payment_id IS NOT NULL AND expense_id IS NULL)",
            name="exactly_one_source",
        ),
        Index("ix_ledger_entries_room_id_effective_at", "room_id", "effective_at"),
        Index("ix_ledger_entries_member_id_effective_at", "member_id", "effective_at"),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("room_members.id", ondelete="RESTRICT"))
    entry_type: Mapped[LedgerEntryType] = mapped_column(str_enum(LedgerEntryType))
    expense_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="RESTRICT"), index=True
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payments.id", ondelete="RESTRICT"), index=True
    )
    amount_delta: Mapped[int] = mapped_column(BigInteger)
    effective_at: Mapped[datetime] = mapped_column(server_default=func.now())
