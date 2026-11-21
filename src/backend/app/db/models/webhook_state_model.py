from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, SmallInteger, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookState(Base):
    """Singleton row holding the last processed Telegram ``update_id`` (deduplication)."""

    __tablename__ = "webhook_state"
    __table_args__ = (CheckConstraint("id = 1", name="singleton"),)

    id: Mapped[int] = mapped_column(
        SmallInteger, primary_key=True, server_default=text("1"), default=1
    )
    last_update_id: Mapped[int] = mapped_column(BigInteger, server_default=text("0"), default=0)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
