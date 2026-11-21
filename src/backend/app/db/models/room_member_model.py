from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin, str_enum
from app.db.enums import MemberRole

if TYPE_CHECKING:
    from app.db.models.room_model import Room
    from app.db.models.user_model import User


class RoomMember(UUIDPrimaryKeyMixin, Base):
    """Membership of a user in a room (``members`` in the SCRUM-117 ERD)."""

    __tablename__ = "room_members"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id"),
        # BR09: exactly one Room Rep per room (at most one enforced here).
        Index(
            "uq_room_members_one_room_rep",
            "room_id",
            unique=True,
            postgresql_where=text("role = 'ROOM_REP'"),
        ),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MemberRole] = mapped_column(
        str_enum(MemberRole), server_default=text("'MEMBER'"), default=MemberRole.MEMBER
    )
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())

    room: Mapped[Room] = relationship(back_populates="members", lazy="raise")
    user: Mapped[User] = relationship(lazy="joined")
