from __future__ import annotations

import json
import time
from urllib.parse import parse_qsl, quote, urlencode

import pytest

from app.core.init_data import InitDataError, validate_init_data
from tests.helpers import TEST_BOT_TOKEN, base_fields, replace_fields, sign_fields


def expect_error(raw: str, *, token: str = TEST_BOT_TOKEN, **kwargs) -> InitDataError:
    with pytest.raises(InitDataError) as exc_info:
        validate_init_data(raw, token, **kwargs)
    return exc_info.value


def test_valid_init_data() -> None:
    now = int(time.time())
    raw = sign_fields(base_fields(now))
    validated = validate_init_data(raw, TEST_BOT_TOKEN, now=now)
    assert validated.user is not None
    assert validated.user["id"] == 123456789
    assert validated.auth_date == now
    assert validated.chat_type == "supergroup"
    assert validated.chat_instance == "-1234567890123456789"
    assert validated.start_param == "group"
    assert validated.query_id == "AAH-test-query-id"


def test_deterministic_vector() -> None:
    fields = {
        "auth_date": "1700000000",
        "query_id": "AAH-test",
        "signature": "test-signature",
        "user": json.dumps(
            {"id": 123, "first_name": "Nam", "username": "nam"},
            separators=(",", ":"),
            ensure_ascii=False,
        ),
    }
    raw = sign_fields(fields)
    parsed = dict(parse_qsl(raw))
    assert parsed["hash"] == "f6a707d15cbac395ca3473eee9437b1f40c6e3cd824dd312c898c912511b8b88"


def test_tampered_user_is_rejected() -> None:
    now = int(time.time())
    raw = sign_fields(base_fields(now))
    tampered_user = json.dumps(
        {"id": 999, "first_name": "Mallory", "username": "mallory"},
        separators=(",", ":"),
    )
    tampered = replace_fields(raw, user=tampered_user)
    error = expect_error(tampered, now=now)
    assert error.code == "INVALID_SIGNATURE"
    assert error.status_code == 401


def test_missing_hash_is_rejected() -> None:
    raw = sign_fields(base_fields())
    parsed = dict(parse_qsl(raw))
    parsed.pop("hash")
    without_hash = urlencode(parsed, quote_via=quote, safe="")
    error = expect_error(without_hash)
    assert error.code == "INVALID_INIT_DATA"
    assert error.status_code == 400


def test_malformed_hash_is_rejected() -> None:
    raw = sign_fields(base_fields())
    malformed = replace_fields(raw, hash="not-a-hash")
    error = expect_error(malformed)
    assert error.code == "INVALID_SIGNATURE"
    assert error.status_code == 401


def test_expired_auth_date_is_rejected() -> None:
    now = int(time.time())
    raw = sign_fields(base_fields(now - 7200))
    error = expect_error(raw, now=now, max_age_seconds=3600)
    assert error.code == "EXPIRED_INIT_DATA"
    assert error.status_code == 401


def test_future_auth_date_is_rejected() -> None:
    now = int(time.time())
    raw = sign_fields(base_fields(now + 3600))
    error = expect_error(raw, now=now)
    assert error.code == "EXPIRED_INIT_DATA"


def test_missing_auth_date_is_rejected() -> None:
    fields = base_fields()
    fields.pop("auth_date")
    raw = sign_fields(fields)
    error = expect_error(raw)
    assert error.code == "EXPIRED_INIT_DATA"


def test_non_integer_auth_date_is_rejected() -> None:
    raw = sign_fields(base_fields(auth_date="not-a-number"))
    error = expect_error(raw)
    assert error.code == "EXPIRED_INIT_DATA"


def test_duplicate_keys_are_rejected() -> None:
    now = int(time.time())
    raw = sign_fields(base_fields(now))
    duplicated = f"{raw}&auth_date={now}"
    error = expect_error(duplicated, now=now)
    assert error.code == "INVALID_INIT_DATA"
    assert error.status_code == 400


def test_empty_and_oversized_init_data_are_rejected() -> None:
    empty_error = expect_error("")
    assert empty_error.code == "INVALID_INIT_DATA"
    assert empty_error.status_code == 400

    oversized_error = expect_error("a=" + ("x" * 9000))
    assert oversized_error.code == "INIT_DATA_TOO_LARGE"
    assert oversized_error.status_code == 413


def test_malformed_query_string_is_rejected() -> None:
    error = expect_error("auth_date")
    assert error.code == "INVALID_INIT_DATA"
    assert error.status_code == 400


def test_signature_must_be_part_of_the_hmac() -> None:
    fields = base_fields()
    fields.pop("signature")
    without_signature = sign_fields(fields)
    with_signature = f"{without_signature}&signature=test-signature"
    error = expect_error(with_signature)
    assert error.code == "INVALID_SIGNATURE"

    signed_with_signature = sign_fields({**fields, "signature": "test-signature"})
    validated = validate_init_data(signed_with_signature, TEST_BOT_TOKEN)
    assert validated.user is not None


def test_wrong_bot_token_is_rejected() -> None:
    raw = sign_fields(base_fields(), bot_token="999:OTHER_TOKEN")
    error = expect_error(raw)
    assert error.code == "INVALID_SIGNATURE"


def test_unicode_and_plus_are_parsed_correctly() -> None:
    now = int(time.time())
    fields = base_fields(now)
    user = json.loads(fields["user"])
    user["first_name"] = "Nam + Hào"
    user["last_name"] = "Nguyễn"
    fields["user"] = json.dumps(user, separators=(",", ":"), ensure_ascii=False)
    raw = sign_fields(fields)
    validated = validate_init_data(raw, TEST_BOT_TOKEN, now=now)
    assert validated.user is not None
    assert validated.user["first_name"] == "Nam + Hào"
    assert validated.user["last_name"] == "Nguyễn"


def test_invalid_user_payload_is_rejected() -> None:
    raw = sign_fields(base_fields(user="not-json"))
    error = expect_error(raw)
    assert error.code == "INVALID_INIT_DATA"
    assert error.status_code == 400

    user_without_id = json.dumps({"first_name": "Nam"}, separators=(",", ":"))
    error = expect_error(sign_fields(base_fields(user=user_without_id)))
    assert error.code == "INVALID_INIT_DATA"
    assert error.status_code == 400


def test_chat_payload_is_parsed() -> None:
    fields = base_fields(
        chat=json.dumps(
            {"id": -1001234567890, "type": "supergroup", "title": "TroMate test"},
            separators=(",", ":"),
        )
    )
    validated = validate_init_data(sign_fields(fields), TEST_BOT_TOKEN)
    assert validated.chat is not None
    assert validated.chat["id"] == -1001234567890
    assert validated.chat["type"] == "supergroup"
