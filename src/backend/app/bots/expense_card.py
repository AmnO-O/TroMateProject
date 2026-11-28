"""Telegram HTML card renderer and inline keyboard builder for UC01 expenses."""

from __future__ import annotations

from datetime import UTC, timedelta, timezone
from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bots.interface import (
    ConfirmationCardDTO,
    DraftSummaryDTO,
    build_agree_callback,
    build_draft_cancel_callback,
    build_draft_edit_callback,
    build_draft_share_callback,
    build_draft_turn_off_callback,
)
from app.services.durations import format_duration_vi

_VN_TZ = timezone(timedelta(hours=7))

_DECISION_LABELS = {
    "AGREE": "✓ Đồng ý",
    "REJECT": "✕ Từ chối",
    "PENDING": "⏳ Chờ duyệt",
}


def _decision_label(decision: str) -> str:
    return escape(_DECISION_LABELS.get(decision, decision))


_STATUS_LABELS: dict[str, str] = {
    "PENDING": "Chờ xác nhận",
    "CONFIRMED": "Đã xác nhận",
    "DRAFT": "Bản nháp",
    "DISPUTED": "Đã từ chối",
    "CANCELLED": "Đã hủy",
}


def format_review_window(minutes: int) -> str:
    """Format a review window in minutes into Vietnamese days/hours/minutes."""

    return format_duration_vi(minutes)


def render_draft_summary_html(summary: DraftSummaryDTO) -> str:
    """Format the UC01 v3.0 draft summary card shown to the group before sharing."""

    lines = [
        "📝 <b>Xem lại khoản chi (bản nháp)</b>",
        f"🧾 <b>{escape(summary.description)}</b>",
        f"💰 Tổng tiền: <b>{summary.total_amount:,}đ</b>",
        f"🏷️ Danh mục: {escape(summary.category_name)}",
        f"👤 Người trả: {escape(summary.payer_name)}",
        "",
        "<b>Chi tiết chia tiền:</b>",
    ]
    for split in summary.splits:
        lines.append(f"• {escape(split.display_name)}: {split.share_amount:,}đ")

    if summary.auto_confirm_enabled and summary.room_window_minutes is not None:
        window_label = format_review_window(summary.room_window_minutes)
        lines.append(
            f"\n⏱️ Tự động xác nhận: <b>Bật</b> (window phòng: <b>{window_label}</b>)"
        )
    elif summary.manual_reason == "NO_ROOM_WINDOW" or summary.room_window_minutes is None:
        lines.append(
            "\n🔒 Tự động xác nhận: <b>Duyệt thủ công</b> — "
            "Phòng chưa có window auto-confirm (BR03)"
        )
    elif summary.manual_reason == "CREATOR_DISABLED":
        window_label = format_review_window(summary.room_window_minutes)
        lines.append(
            "\n🔒 Tự động xác nhận: <b>Đã tắt (Duyệt thủ công)</b> "
            f"(window phòng: {window_label})"
        )
    elif summary.manual_reason == "MANUAL_CATEGORY":
        lines.append(
            "\n🔒 Tự động xác nhận: <b>Duyệt thủ công (BR02)</b> — "
            "Danh mục này luôn cần duyệt thủ công"
        )
    else:
        lines.append(
            "\n🔒 Tự động xác nhận: <b>Duyệt thủ công (BR02)</b> — "
            "Khoản chi không phải text cần duyệt thủ công"
        )

    return "\n".join(lines)


def build_draft_summary_keyboard(summary: DraftSummaryDTO) -> InlineKeyboardMarkup:
    """Build inline buttons for the UC01 v3.0 draft summary."""

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="✓ Chia sẻ",
                callback_data=build_draft_share_callback(summary.draft_id),
            ),
            InlineKeyboardButton(
                text="✎ Chỉnh sửa",
                callback_data=build_draft_edit_callback(summary.draft_id),
            ),
            InlineKeyboardButton(
                text="✕ Hủy",
                callback_data=build_draft_cancel_callback(summary.draft_id),
            ),
        ]
    ]
    if summary.auto_confirm_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔕 Tắt tự động xác nhận",
                    callback_data=build_draft_turn_off_callback(summary.draft_id),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def render_confirmation_card_html(card: ConfirmationCardDTO) -> str:
    """Format a ``PENDING`` expense confirmation card aligned with UI Design (SCRUM-121)."""

    status_label = _STATUS_LABELS.get(card.status, card.status)
    status_line = (
        f"📌 Trạng thái: <b>{escape(status_label)} (Duyệt thủ công — BR02)</b>"
        if card.review_deadline is None and card.status == "PENDING"
        else f"📌 Trạng thái: <b>{escape(status_label)}</b>"
    )

    payer_line = f"👤 Người trả: {escape(card.payer_name)}"
    if card.voter_count:
        payer_line += f" · {_decision_label(card.payer_decision)}"

    lines = [
        f"🧾 <b>{escape(card.description)}</b>",
        f"💰 Tổng tiền: <b>{card.total_amount:,}đ</b>",
        f"🏷️ Danh mục: {escape(card.category_name)}",
        payer_line,
        status_line,
        "",
        "<b>Chi tiết chia tiền:</b>",
    ]
    for split in card.splits:
        lines.append(f"• {escape(split.display_name)}: {split.share_amount:,}đ")

        if card.voter_count:
            lines[-1] += f" · {_decision_label(split.decision)}"

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
    if card.split_method:
        methods = {
            "EQUAL": "Chia đều",
            "CUSTOM_AMOUNT": "Theo số tiền",
            "CUSTOM_RATIO": "Theo tỷ lệ",
        }
        lines.append(f"Cách chia: {escape(methods.get(card.split_method, card.split_method))}")
    if card.rejection:
        lines.append(f"Lý do từ chối: {escape(card.rejection)}")
    if card.balances:
        lines.append("Số dư sau xác nhận:")
        lines.extend(f"{escape(name)}: {value:+,}đ" for name, value in card.balances)
    return "\n".join(lines)


def build_confirmation_keyboard(card: ConfirmationCardDTO) -> InlineKeyboardMarkup:
    """Build ``[✓ Đồng ý]``, ``[✕ Từ chối]``, and ``[✎ Chỉnh sửa]`` buttons."""

    def link(label, action):
        return InlineKeyboardButton(text=label, url=card.miniapp_edit_url + "_" + action)

    edit = link("✎ Chỉnh sửa", "edit")
    cancel = link("Hủy khoản chi", "cancel")
    if card.status == "DRAFT":
        rows = [
            [
                InlineKeyboardButton(
                    text="Chia sẻ vào nhóm",
                    callback_data=f"expense:share:{card.expense_id}:{card.version}",
                ),
                edit,
                cancel,
            ]
        ]
    elif card.status == "DISPUTED":
        rows = [[link("Thêm lý do", "addreason"), edit, cancel]]
    else:
        rows = [
            [
                InlineKeyboardButton(
                    text="✓ Đồng ý",
                    callback_data=build_agree_callback(card.expense_id, card.version),
                ),
                link("✕ Từ chối", "reject"),
                edit,
            ],
            [cancel],
        ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
