from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402

DEFAULT_ALLOWED_UPDATES = ["message", "callback_query", "my_chat_member"]


def call_bot_api(token: str, method: str, payload: dict[str, Any] | None = None) -> Any:
    url = f"https://api.telegram.org/bot{token}/{method}"
    with httpx.Client(timeout=20) as client:
        response = client.post(url, json=payload or {})
    try:
        data = response.json()
    except ValueError as exc:
        raise SystemExit(f"Telegram returned a non-JSON response ({response.status_code})") from exc
    if not response.is_success or not data.get("ok"):
        description = data.get("description", response.text)
        raise SystemExit(f"{method} failed: {description}")
    return data.get("result")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the Telegram webhook for TroMate.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="Register the webhook")
    set_parser.add_argument("--url", help="Public HTTPS webhook URL; defaults to PUBLIC_BASE_URL")
    set_parser.add_argument("--drop-pending", action="store_true")
    set_parser.add_argument("--max-connections", type=int, default=10)

    subparsers.add_parser("info", help="Show getWebhookInfo")

    delete_parser = subparsers.add_parser("delete", help="Delete the webhook")
    delete_parser.add_argument("--drop-pending", action="store_true")

    args = parser.parse_args()
    settings = Settings()

    if args.command == "set":
        webhook_url = args.url or settings.webhook_url
        if not webhook_url:
            raise SystemExit("Provide --url or set PUBLIC_BASE_URL")
        payload = {
            "url": webhook_url,
            "secret_token": settings.telegram_webhook_secret,
            "allowed_updates": DEFAULT_ALLOWED_UPDATES,
            "max_connections": args.max_connections,
            "drop_pending_updates": args.drop_pending,
        }
        call_bot_api(settings.telegram_bot_token, "setWebhook", payload)
        print(f"Webhook set to {webhook_url}")
        print(json.dumps(call_bot_api(settings.telegram_bot_token, "getWebhookInfo"), indent=2))
    elif args.command == "info":
        info = call_bot_api(settings.telegram_bot_token, "getWebhookInfo")
        print(json.dumps(info, indent=2, ensure_ascii=False))
    elif args.command == "delete":
        call_bot_api(
            settings.telegram_bot_token,
            "deleteWebhook",
            {"drop_pending_updates": args.drop_pending},
        )
        print("Webhook deleted")


if __name__ == "__main__":
    main()
