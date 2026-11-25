"""Telegram HTML card renderer and inline keyboard builder for UC01 expenses."""

from __future__ import annotations

from datetime import UTC, timedelta, timezone
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bots.interface import (
    ConfirmationCardDTO,
    build_agree_callback,
    build_edit_callback,
    build_reject_callback,
)

_VN_TZ = timezone(timedelta(hours=7))

_STATUS_LABELS: dict[str, str] = {
    "PENDING": "Chờ xác nhận",
    "CONFIRMED": "Đã xác nhận",
    "DISPUTED": "Đã từ chối",
    "CANCELLED": "Đã hủy",
}


def render_confirmation_card_html(card: ConfirmationCardDTO) -> str:
    """Format a ``PENDING`` expense confirmation card aligned with UI Design (SCRUM-121)."""

    status_label = _STATUS_LABELS.get(card.status, card.status)
    status_line = (
        f"📌 Trạng thái: <b>{escape(status_label)} (Duyệt thủ công — BR02)</b>"
        if card.review_deadline is None and card.status == "PENDING"
        else f"📌 Trạng thái: <b>{escape(status_label)}</b>"
    )

    lines = [
        f"🧾 <b>{escape(card.description)}</b>",
        f"💰 Tổng tiền: <b>{card.total_amount:,}đ</b>",
        f"🏷️ Danh mục: {escape(card.category_name)}",
        f"👤 Người trả: {escape(card.payer_name)}",
        status_line,
        "",
        "<b>Chi tiết chia tiền:</b>",
    ]
    if card.voter_count:
        lines.append(f"{escape(card.payer_name)} (payer): {escape(card.payer_decision)}")
    for split in card.splits:
        lines.append(f"• {escape(split.display_name)}: {split.share_amount:,}đ")

        if card.voter_count:
            lines[-1] += f" · {escape(split.decision)}"

    if card.status == "PENDING" and card.review_deadline is not None:
        deadline_dt = (
            card.review_deadline.replace(tzinfo=UTC)
            if card.review_deadline.tzinfo is None
            else card.review_deadline
        )
        deadline_str = deadline_dt.astimezone(_VN_TZ).strftime("%H:%M %d/%m (GMT+7)")
        lines.append(f"\n⏳ Hạn xác nhận: {deadline_str}")
    elif card.status == "PENDING":
        lines.append("\n🔒 Không tự động xác nhận (bắt buộc 100% thành viên đồng ý)")

    if card.voter_count:
        lines.append(f"Đồng ý: {card.agreed_count}/{card.voter_count}")
    return "\n".join(lines)


def build_confirmation_keyboard(card: ConfirmationCardDTO) -> InlineKeyboardMarkup:
    """Build ``[✓ Đồng ý]``, ``[✕ Từ chối]``, and ``[✎ Chỉnh sửa]`` buttons."""

    edit_button = InlineKeyboardButton(
        text="✎ Chỉnh sửa",
        callback_data=build_edit_callback(card.expense_id, card.version),
    )
    if card.status == "DISPUTED":
        return InlineKeyboardMarkup(inline_keyboard=[[edit_button]])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✓ Đồng ý",
                    callback_data=build_agree_callback(card.expense_id, card.version),
                ),
                InlineKeyboardButton(
                    text="✕ Từ chối",
                    callback_data=build_reject_callback(card.expense_id, card.version),
                ),
                edit_button,
            ]
        ]
    )
