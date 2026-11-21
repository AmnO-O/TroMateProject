from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, str_enum
from app.db.enums import PaymentStatus


class Payment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A VietQR settlement transfer between two members of a room."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("payer_member_id <> recipient_member_id", name="payer_not_recipient"),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    payer_member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("room_members.id", ondelete="RESTRICT")
    )
    recipient_member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("room_members.id", ondelete="RESTRICT")
    )
    bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="SET NULL")
    )
    amount: Mapped[int] = mapped_column(BigInteger)  # whole VND
    vietqr_payload: Mapped[str] = mapped_column(Text)
    status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus), server_default=text("'PENDING'"), default=PaymentStatus.PENDING
    )
    proof_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="SET NULL")
    )
    paid_at: Mapped[datetime | None]
    received_at: Mapped[datetime | None]
