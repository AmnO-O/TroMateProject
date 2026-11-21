from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Global Telegram identity; room-scoped data lives in ``room_members``."""

    __tablename__ = "users"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(128))
    is_operator: Mapped[bool] = mapped_column(server_default=false(), default=False)
    # users <-> bank_accounts is a cycle; use_alter adds this FK after both tables exist.
    default_bank_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bank_accounts.id", ondelete="SET NULL", use_alter=True)
    )
