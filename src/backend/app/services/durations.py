"""Duration rules shared by services (BR03, SCRUM-138).

The limits come from :class:`app.core.config.DurationSettings`, never from constants, so the
test environment can shorten them through ``.env``.
"""

from __future__ import annotations

from app.core.config import DurationSettings, get_duration_settings
from app.services.errors import ValidationError


def format_duration_vi(minutes: int) -> str:
    """Format a duration in minutes as Vietnamese days/hours/minutes, e.g. ``1 ngày 12 giờ``."""

    days, rem_minutes = divmod(minutes, 1440)
    hours, mins = divmod(rem_minutes, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days} ngày")
    if hours:
        parts.append(f"{hours} giờ")
    if mins or not parts:
        parts.append(f"{mins} phút")
    return " ".join(parts)


def validate_review_window(minutes: int, durations: DurationSettings | None = None) -> int:
    """Check a proposed auto-confirmation window against the limits in effect (UC13-AF05).

    Raises :class:`ValidationError` whose message shows those limits, e.g.
    ``từ 1 ngày đến 30 ngày`` with the production configuration.
    """

    durations = durations or get_duration_settings()
    low, high = durations.review_window_min_minutes, durations.review_window_max_minutes
    if not low <= minutes <= high:
        raise ValidationError(
            "Thời gian tự động xác nhận phải từ "
            f"{format_duration_vi(low)} đến {format_duration_vi(high)}."
        )
    return minutes
