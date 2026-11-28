from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, str_enum
from app.db.enums import PlanType, ReviewDefaultAction

if TYPE_CHECKING:
    from app.db.models.room_member_model import RoomMember


class Room(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A roommate group bound to one Telegram group chat."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("scans_remaining >= 0", name="scans_remaining_non_negative"),
        # BR03 (v3.0): NULL until adopted via UC13. The allowed range is configurable
        # (DurationSettings) and validated by the application, so the DB only checks > 0.
        CheckConstraint(
            "review_timeout_minutes IS NULL OR review_timeout_minutes > 0",
            name="review_timeout_allowed",
        ),
    )

    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String(128))
    plan_type: Mapped[PlanType] = mapped_column(
        str_enum(PlanType), server_default=text("'FREE'"), default=PlanType.FREE
    )
    scans_remaining: Mapped[int] = mapped_column(server_default=text("10"), default=10)
    # BR03 (v3.0): NULL until the room adopts a window via UC13 (production: 1–30 days).
    review_timeout_minutes: Mapped[int | None] = mapped_column(default=None)
    review_default_action: Mapped[ReviewDefaultAction] = mapped_column(
        str_enum(ReviewDefaultAction),
        server_default=text("'CONFIRM'"),
        default=ReviewDefaultAction.CONFIRM,
    )

    members: Mapped[list[RoomMember]] = relationship(
        back_populates="room", lazy="selectin", order_by="RoomMember.joined_at"
    )
