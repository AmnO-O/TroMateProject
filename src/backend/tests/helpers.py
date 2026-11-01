from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import quote, urlencode

TEST_BOT_TOKEN = "123456:TEST_TOKEN"
TEST_WEBHOOK_SECRET = "test-secret-0123456789abcdef"


def base_fields(now: int | None = None, **overrides: str) -> dict[str, str]:
    timestamp = int(time.time()) if now is None else now
    user = {
        "id": 123456789,
        "first_name": "Nam",
        "last_name": "Hào",
        "username": "nam",
        "language_code": "vi",
        "is_premium": False,
    }
    fields = {
        "auth_date": str(timestamp),
        "query_id": "AAH-test-query-id",
        "user": json.dumps(user, separators=(",", ":"), ensure_ascii=False),
        "chat_type": "supergroup",
        "chat_instance": "-1234567890123456789",
        "start_param": "group",
        "signature": "test-signature",
    }
    fields.update(overrides)
    return fields


def sign_fields(fields: dict[str, str], bot_token: str = TEST_BOT_TOKEN) -> str:
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    digest = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return urlencode({**fields, "hash": digest}, quote_via=quote, safe="")


def replace_fields(raw_init_data: str, **updates: str) -> str:
    from urllib.parse import parse_qsl

    fields = dict(parse_qsl(raw_init_data, keep_blank_values=True))
    fields.update(updates)
    return urlencode(fields, quote_via=quote, safe="")
