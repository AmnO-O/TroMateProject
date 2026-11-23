from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class UsageEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only analytics event for operator statistics (DAU/MAU, peak hours)."""

    __tablename__ = "usage_events"
    __table_args__ = (
        Index("ix_usage_events_created_at", "created_at"),
        Index("ix_usage_events_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    room_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(64))
