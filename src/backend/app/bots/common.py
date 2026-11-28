from __future__ import annotations

import logging
from datetime import timedelta, timezone

from app.services.balance_service import BalanceService, RoomBalances

logger = logging.getLogger(__name__)

VIETNAM_TZ = timezone(timedelta(hours=7), "GMT+7")
GROUP_CHAT_TYPES = frozenset({"group", "supergroup"})

BALANCE_PRIVATE_CHAT_TEXT = (
    "Dùng /balance trong nhóm phòng trọ để xem số dư của phòng,\nhoặc mở Mini App từ nhóm đó."
)
BALANCE_UNAVAILABLE_TEXT = "⚠️ Chưa tải được số dư. Vui lòng thử lại sau."


def format_vnd(amount: int, *, signed: bool = False) -> str:
    sign = ("+" if amount > 0 else "-" if amount < 0 else "") if signed else ""
    return f"{sign}{abs(amount):,}đ"


def balance_text(summary: RoomBalances | None) -> str:
    """Plain-text ``/balance`` reply built from live ledger balances (no parse mode)."""

    if summary is None:
        return (
            "Phòng này chưa có dữ liệu chi tiêu.\n"
            "Dùng /new để ghi khoản chi đầu tiên, ví dụ: /new Đi chợ 150k chia đều cả phòng"
        )

    lines = [f"Số dư phòng {summary.room_name} (VND)"]
    if summary.is_settled:
        lines.append("Mọi người đã cân bằng, không ai nợ ai. ✅")
    else:
        for item in summary.balances:
            note = " (được nhận)" if item.amount > 0 else " (cần trả)" if item.amount < 0 else ""
            lines.append(f"• {item.display_name}: {format_vnd(item.amount, signed=True)}{note}")
    if summary.transfers:
        lines.append("")
        lines.append("Gợi ý thanh toán:")
        lines.extend(
            f"• {t.from_name} → {t.to_name}: {format_vnd(t.amount)}" for t in summary.transfers
        )
    lines.append("")
    lines.append("Chỉ tính các khoản chi đã xác nhận.")
    updated = summary.generated_at.astimezone(VIETNAM_TZ).strftime("%d/%m/%Y %H:%M:%S")
    lines.append(f"Cập nhật: {updated} (GMT+7)")
    return "\n".join(lines)


async def live_balance_text(service: BalanceService, chat_id: int, chat_type: str) -> str:
    """Load the room's balances for a ``/balance`` command or its refresh button."""

    if chat_type not in GROUP_CHAT_TYPES:
        return BALANCE_PRIVATE_CHAT_TEXT
    try:
        summary = await service.get_room_balances(chat_id)
    except Exception:
        logger.exception("Could not load balances for chat %s", chat_id)
        return BALANCE_UNAVAILABLE_TEXT
    return balance_text(summary)


def start_text(library: str, username: str) -> str:
    return (
        f"TroMate spike is running via {library}.\n\n"
        "Commands:\n"
        "/start - show this message\n"
        "/new [text] - log a shared expense in group chat\n"
        "/balance - show room balances (in group chat)\n"
        "/app - open the Mini App\n"
        "/help - show help\n\n"
        "Tap the button below to open the Mini App."
    )


def group_start_text(library: str, username: str, chat_id: int | None = None) -> str:
    return (
        f"TroMate spike is running via {library}.\n\n"
        f"Open the Mini App: {miniapp_direct_link(username, chat_id)}\n\n"
        f"Group commands: /new@{username or 'your_bot'}, "
        f"/balance@{username or 'your_bot'} and /app@{username or 'your_bot'}"
    )


def help_text(library: str) -> str:
    return (
        "Danh sách lệnh TroMate:\n"
        "/start - Khởi động bot và lấy link mở Mini App\n"
        "/new [nội dung] - Ghi nhận chi tiêu chung (vd: /new Đi chợ 150k chia tao với Nam)\n"
        "  (Chế độ dự phòng: ghi rõ người tham gia sau 'chia ...', vd: chia tao với Nam)\n"
        "/balance - Xem số dư công nợ của phòng (từ các khoản chi đã xác nhận)\n"
        "/app - Mở giao diện Mini App\n"
        "/help - Xem hướng dẫn này\n\n"
        f"Thư viện bot đang chạy: {library}"
    )


def miniapp_direct_link(username: str, chat_id: int | None = None) -> str:
    """Direct Mini App link; with ``chat_id`` the app opens on that room's balances.

    ``start_param`` only allows ``[A-Za-z0-9_-]``, which covers negative group ids. It is
    chosen by whoever builds the link, so the API still checks the viewer belongs to the room.
    """

    start = f"room_{chat_id}" if chat_id is not None else "group"
    return f"https://t.me/{username or 'your_bot'}?startapp={start}"
