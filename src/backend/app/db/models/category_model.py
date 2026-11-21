from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, false, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class Category(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Default (system) and Room Rep-defined expense categories."""

    __tablename__ = "categories"
    __table_args__ = (
        # BR06: 2-30 characters, unique in the room ignoring letter case.
        CheckConstraint("char_length(name) BETWEEN 2 AND 30", name="name_length"),
        Index("uq_categories_room_id_lower_name", "room_id", text("lower(name)"), unique=True),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    created_by_member_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("room_members.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(30))
    is_default: Mapped[bool] = mapped_column(server_default=false(), default=False)
    is_archived: Mapped[bool] = mapped_column(server_default=false(), default=False)
