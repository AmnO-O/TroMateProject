from __future__ import annotations

import uuid

from sqlalchemy import CHAR, BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Attachment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Metadata for an image stored in Cloudflare R2 (the bytes never enter PostgreSQL)."""

    __tablename__ = "attachments"
    __table_args__ = (CheckConstraint("size_bytes > 0", name="size_bytes_positive"),)

    room_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    uploaded_by_member_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("room_members.id", ondelete="RESTRICT")
    )
    object_key: Mapped[str] = mapped_column(String(512), unique=True)
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256_hash: Mapped[str] = mapped_column(CHAR(64))
