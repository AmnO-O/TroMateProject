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
        "/balance - show mock balances\n"
        "/app - open the Mini App\n"
        "/help - show help\n\n"
        "Tap the button below to open the Mini App."
    )


def group_start_text(library: str, username: str) -> str:
    return (
        f"TroMate spike is running via {library}.\n\n"
        f"Open the Mini App: {miniapp_direct_link(username)}\n\n"
        f"Group commands: /balance@{username or 'your_bot'} and /app@{username or 'your_bot'}"
    )


def help_text(library: str) -> str:
    return (
        "Available commands:\n"
        "/start - show the Mini App launcher\n"
        "/balance - show mock balances\n"
        "/app - open the Mini App\n"
        "/help - show this help\n\n"
        f"Active library: {library}"
    )


def miniapp_direct_link(username: str) -> str:
    return f"https://t.me/{username or 'your_bot'}?startapp=group"
