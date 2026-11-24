"""Telegram HTML card renderer and inline keyboard builder for UC01 expenses."""

from __future__ import annotations

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bots.interface import (
    ConfirmationCardDTO,
    build_agree_callback,
    build_edit_callback,
    build_reject_callback,
)


def render_confirmation_card_html(card: ConfirmationCardDTO) -> str:
    """Format a ``PENDING`` expense confirmation card as safe Telegram HTML."""

    lines = [
        f"🧾 <b>{escape(card.description)}</b>",
        f"💰 Tổng tiền: <b>{card.total_amount:,}đ</b>",
        f"🏷️ Danh mục: {escape(card.category_name)}",
        f"👤 Người trả: {escape(card.payer_name)}",
        f"📌 Trạng thái: <code>{escape(card.status)}</code>",
        "",
        "<b>Chi tiết chia tiền:</b>",
    ]
    for split in card.splits:
        lines.append(f"• {escape(split.display_name)}: {split.share_amount:,}đ")

    if card.review_deadline is not None:
        deadline_str = card.review_deadline.strftime("%H:%M %d/%m UTC")
        lines.append(f"\n⏳ Hạn xác nhận: {deadline_str}")
    else:
        lines.append("\n🔒 Cần xác nhận thủ công")

    return "\n".join(lines)


def build_confirmation_keyboard(card: ConfirmationCardDTO) -> InlineKeyboardMarkup:
    """Build ``[Agree]``, ``[Reject]``, and ``[Edit]`` buttons for a pending expense."""

    edit_button = (
        InlineKeyboardButton(text="✏️ Edit", url=card.miniapp_edit_url)
        if card.miniapp_edit_url
        else InlineKeyboardButton(
            text="✏️ Edit",
            callback_data=build_edit_callback(card.expense_id),
        )
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Agree",
                    callback_data=build_agree_callback(card.expense_id, card.version),
                ),
                InlineKeyboardButton(
                    text="❌ Reject",
                    callback_data=build_reject_callback(card.expense_id, card.version),
                ),
                edit_button,
            ]
        ]
    )
