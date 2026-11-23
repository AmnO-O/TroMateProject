from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, str_enum
from app.db.enums import REVIEW_WINDOW_MINUTES, PlanType, ReviewDefaultAction

if TYPE_CHECKING:
    from app.db.models.room_member_model import RoomMember

_WINDOWS = ", ".join(str(m) for m in REVIEW_WINDOW_MINUTES)


class Room(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A roommate group bound to one Telegram group chat."""

    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("scans_remaining >= 0", name="scans_remaining_non_negative"),
        # BR03: allowed auto-confirmation windows.
        CheckConstraint(f"review_timeout_minutes IN ({_WINDOWS})", name="review_timeout_allowed"),
    )

    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String(128))
    plan_type: Mapped[PlanType] = mapped_column(
        str_enum(PlanType), server_default=text("'FREE'"), default=PlanType.FREE
    )
    scans_remaining: Mapped[int] = mapped_column(server_default=text("10"), default=10)
    review_timeout_minutes: Mapped[int] = mapped_column(server_default=text("5"), default=5)
    review_default_action: Mapped[ReviewDefaultAction] = mapped_column(
        str_enum(ReviewDefaultAction),
        server_default=text("'CONFIRM'"),
        default=ReviewDefaultAction.CONFIRM,
    )

    members: Mapped[list[RoomMember]] = relationship(
        back_populates="room", lazy="selectin", order_by="RoomMember.joined_at"
    )
