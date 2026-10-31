from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


class InitDataError(ValueError):
    """A safe, structured error raised when Mini App init data is invalid."""

    def __init__(self, code: str, message: str, status_code: int = 401) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class ValidatedInitData:
    user: dict[str, Any] | None
    auth_date: int
    query_id: str | None
    chat: dict[str, Any] | None
    chat_type: str | None
    chat_instance: str | None
    start_param: str | None
    fields: dict[str, str]


def _parse_json_object(raw: str, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InitDataError(
            "INVALID_INIT_DATA",
            f"{field_name} is not valid JSON",
            status_code=400,
        ) from exc
    if not isinstance(value, dict):
        raise InitDataError(
            "INVALID_INIT_DATA",
            f"{field_name} must be a JSON object",
            status_code=400,
        )
    return value


def validate_init_data(
    raw_init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 3600,
    max_length: int = 8192,
    now: float | None = None,
) -> ValidatedInitData:
    """Validate Telegram Mini App ``initData`` using the official bot-token HMAC.

    The data-check-string includes every field except ``hash``. In particular,
    ``signature`` (added by newer Bot API versions) stays in the HMAC input.
    """

    if not raw_init_data or not raw_init_data.strip():
        raise InitDataError("INVALID_INIT_DATA", "initData is empty", status_code=400)
    if len(raw_init_data) > max_length:
        raise InitDataError(
            "INIT_DATA_TOO_LARGE",
            f"initData exceeds {max_length} characters",
            status_code=413,
        )

    try:
        pairs = parse_qsl(
            raw_init_data,
            keep_blank_values=True,
            strict_parsing=True,
        )
    except ValueError as exc:
        raise InitDataError(
            "INVALID_INIT_DATA",
            "initData is not a valid query string",
            status_code=400,
        ) from exc

    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise InitDataError(
            "INVALID_INIT_DATA",
            "initData contains duplicate keys",
            status_code=400,
        )

    fields = dict(pairs)
    provided_hash = fields.pop("hash", None)
    if provided_hash is None:
        raise InitDataError("INVALID_INIT_DATA", "initData is missing hash", status_code=400)
    if not re.fullmatch(r"[0-9a-fA-F]{64}", provided_hash):
        raise InitDataError(
            "INVALID_SIGNATURE",
            "initData hash must be 64 hexadecimal characters",
            status_code=401,
        )

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, provided_hash.lower()):
        raise InitDataError(
            "INVALID_SIGNATURE",
            "initData signature is invalid",
            status_code=401,
        )

    auth_date_raw = fields.get("auth_date")
    if auth_date_raw is None:
        raise InitDataError(
            "EXPIRED_INIT_DATA",
            "initData is missing auth_date",
            status_code=401,
        )
    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        raise InitDataError(
            "EXPIRED_INIT_DATA",
            "initData auth_date is not an integer",
            status_code=401,
        ) from exc

    now_ts = int(time.time() if now is None else now)
    if auth_date > now_ts + 60:
        raise InitDataError(
            "EXPIRED_INIT_DATA",
            "initData auth_date is in the future",
            status_code=401,
        )
    if now_ts - auth_date > max_age_seconds:
        raise InitDataError(
            "EXPIRED_INIT_DATA",
            "initData has expired",
            status_code=401,
        )

    user: dict[str, Any] | None = None
    if "user" in fields:
        user = _parse_json_object(fields["user"], "user")
        user_id = user.get("id")
        if not isinstance(user_id, int) or isinstance(user_id, bool):
            raise InitDataError(
                "INVALID_INIT_DATA",
                "user.id must be an integer",
                status_code=400,
            )

    chat: dict[str, Any] | None = None
    if "chat" in fields:
        chat = _parse_json_object(fields["chat"], "chat")

    return ValidatedInitData(
        user=user,
        auth_date=auth_date,
        query_id=fields.get("query_id"),
        chat=chat,
        chat_type=fields.get("chat_type"),
        chat_instance=fields.get("chat_instance"),
        start_param=fields.get("start_param"),
        fields=fields,
    )
