from __future__ import annotations

from datetime import UTC, datetime

from app.core.sample_data import MOCK_BALANCES


def balance_text() -> str:
    lines = ["Balances (mock, VND)"]
    for item in MOCK_BALANCES:
        amount = int(item["amount"])
        sign = "+" if amount >= 0 else "-"
        lines.append(f"• {item['name']}  {sign}{abs(amount):,}")
    lines.append("")
    lines.append(f"Updated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    return "\n".join(lines)


def start_text(library: str, username: str) -> str:
    return (
        f"TroMate spike is running via {library}.\n\n"
        "Commands:\n"
        "/start - show this message\n"
        "/new [text] - log a shared expense in group chat\n"
        "/balance - show mock balances\n"
        "/app - open the Mini App\n"
        "/help - show help\n\n"
        "Tap the button below to open the Mini App."
    )


def group_start_text(library: str, username: str) -> str:
    return (
        f"TroMate spike is running via {library}.\n\n"
        f"Open the Mini App: {miniapp_direct_link(username)}\n\n"
        f"Group commands: /new@{username or 'your_bot'}, "
        f"/balance@{username or 'your_bot'} and /app@{username or 'your_bot'}"
    )


def help_text(library: str) -> str:
    return (
        "Danh sách lệnh TroMate:\n"
        "/start - Khởi động bot và lấy link mở Mini App\n"
        "/new [nội dung] - Ghi nhận chi tiêu chung (vd: /new Đi chợ 150k chia tao với Nam)\n"
        "  (Chế độ dự phòng: ghi rõ người tham gia sau 'chia ...', vd: chia tao với Nam)\n"
        "/balance - Xem số dư công nợ (dữ liệu mẫu)\n"
        "/app - Mở giao diện Mini App\n"
        "/help - Xem hướng dẫn này\n\n"
        f"Thư viện bot đang chạy: {library}"
    )


def miniapp_direct_link(username: str) -> str:
    return f"https://t.me/{username or 'your_bot'}?startapp=group"
