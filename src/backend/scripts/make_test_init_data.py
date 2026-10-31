from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlencode

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402


def build_init_data(
    bot_token: str,
    *,
    user_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
    language_code: str | None,
    auth_age_seconds: int,
    query_id: str | None,
    chat_id: int | None,
    chat_type: str | None,
    chat_instance: str | None,
    start_param: str | None,
    signature: str | None,
    tamper: bool,
) -> str:
    now = int(time.time())
    user: dict[str, object] = {
        "id": user_id,
        "first_name": first_name,
        "is_bot": False,
    }
    if last_name:
        user["last_name"] = last_name
    if username:
        user["username"] = username
    if language_code:
        user["language_code"] = language_code

    fields: dict[str, str] = {
        "auth_date": str(now - auth_age_seconds),
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
    }
    if query_id:
        fields["query_id"] = query_id
    if chat_id is not None:
        chat: dict[str, object] = {"id": chat_id, "type": chat_type or "supergroup"}
        if chat_type:
            chat["type"] = chat_type
        fields["chat"] = json.dumps(chat, separators=(",", ":"), ensure_ascii=False)
    if chat_type:
        fields["chat_type"] = chat_type
    if chat_instance:
        fields["chat_instance"] = chat_instance
    if start_param:
        fields["start_param"] = start_param
    if signature is not None:
        fields["signature"] = signature

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if tamper:
        replacement = "0" if calculated_hash[-1] != "0" else "1"
        calculated_hash = calculated_hash[:-1] + replacement
    fields["hash"] = calculated_hash
    return urlencode(fields, quote_via=quote, safe="")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEV ONLY: generate signed Telegram Mini App initData for local tests.",
    )
    parser.add_argument("--bot-token", help="Defaults to TELEGRAM_BOT_TOKEN from .env")
    parser.add_argument("--user-id", type=int, default=123456789)
    parser.add_argument("--first-name", default="Nam")
    parser.add_argument("--last-name")
    parser.add_argument("--username", default="tromate_test")
    parser.add_argument("--language-code", default="vi")
    parser.add_argument("--auth-age-seconds", type=int, default=0)
    parser.add_argument("--query-id", default="AAH-test-query-id")
    parser.add_argument("--chat-id", type=int)
    parser.add_argument("--chat-type", default="supergroup")
    parser.add_argument("--chat-instance", default="-1234567890123456789")
    parser.add_argument("--start-param", default="group")
    parser.add_argument("--signature", default="test-signature")
    parser.add_argument("--omit-signature", action="store_true")
    parser.add_argument("--tamper", action="store_true", help="Corrupt the hash for negative tests")
    args = parser.parse_args()

    bot_token = args.bot_token or Settings().telegram_bot_token
    init_data = build_init_data(
        bot_token,
        user_id=args.user_id,
        first_name=args.first_name,
        last_name=args.last_name,
        username=args.username,
        language_code=args.language_code,
        auth_age_seconds=args.auth_age_seconds,
        query_id=args.query_id,
        chat_id=args.chat_id,
        chat_type=args.chat_type,
        chat_instance=args.chat_instance,
        start_param=args.start_param,
        signature=None if args.omit_signature else args.signature,
        tamper=args.tamper,
    )
    print(
        "DEV ONLY: this string is signed with the configured bot token. "
        "Do not paste it into public logs.",
        file=sys.stderr,
    )
    print(init_data)


if __name__ == "__main__":
    main()
