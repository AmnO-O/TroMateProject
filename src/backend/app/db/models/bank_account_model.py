from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class BankAccount(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A user's bank account used to build VietQR payloads."""

    __tablename__ = "bank_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    bank_bin: Mapped[str] = mapped_column(String(16))
    account_number: Mapped[str] = mapped_column(String(32))
    account_name: Mapped[str] = mapped_column(String(128))
