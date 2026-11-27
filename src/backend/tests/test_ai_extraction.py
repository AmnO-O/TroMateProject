# ruff: noqa: E402
"""Subtask 1 tests and latency benchmark: Gemini vs rule-based VND fallback."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

# Ensure imports resolve to this worktree even when pytest uses the root editable .venv
WORKTREE_BACKEND = Path(__file__).resolve().parents[1]
if str(WORKTREE_BACKEND) not in sys.path:
    sys.path.insert(0, str(WORKTREE_BACKEND))

import httpx
import pytest

from app.adapters.ai_extraction import AIExtractionAdapter
from app.adapters.vnd_parser import RawExtractionResult
from app.core.config import Settings

SAMPLE_MESSAGES: tuple[tuple[str, str, str], ...] = (
    ("Đi chợ mua thịt cá hết 150k chia tao với Nam", "150k", "EQUAL"),
    ("Tiền điện tháng 10 650k chia đều cả phòng", "650k", "EQUAL"),
    ("Trà sữa 120k tao trả, Minh 70k, An 50k", "120k", "CUSTOM_AMOUNT"),
    ("Đóng tiền wifi 1 củ rưỡi", "1 củ rưỡi", "EQUAL"),
)


def _load_gemini_key_from_env() -> str:
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    env_file = WORKTREE_BACKEND / ".env"
    if not env_file.exists():
        return ""
    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("GEMINI_API_KEY="):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


async def test_fallback_extraction_and_timing() -> None:
    adapter = AIExtractionAdapter(api_key="")
    timings_ms: list[float] = []
    results: list[RawExtractionResult] = []

    for text, expected_amount, expected_split in SAMPLE_MESSAGES:
        start = time.perf_counter()
        result = await adapter.extract(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings_ms.append(elapsed_ms)

        assert result is not None
        assert result.source == "fallback"
        assert result.raw_amount.lower() == expected_amount.lower()
        assert result.split_type == expected_split
        results.append(result)

    assert results[0].participant_hints == ["tao", "Nam"]
    assert results[1].participant_hints == []
    assert results[2].payer_hint == "tao"
    assert results[2].custom_splits == {"Minh": "70k", "An": "50k"}
    assert results[3].category_hint == "Internet"

    avg_ms = sum(timings_ms) / len(timings_ms)
    print(f"\n[Fallback Timing] avg={avg_ms:.4f} ms | runs={[round(t, 4) for t in timings_ms]}")
    assert avg_ms < 50.0


async def test_gemini_fallback_on_api_failure() -> None:
    def _failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "upstream unavailable"})

    transport = httpx.MockTransport(_failing_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = AIExtractionAdapter(api_key="dummy-key", client=client)
        result = await adapter.extract("Mua nước uống 60k chia tao với Bình")

    assert result is not None
    assert result.source == "fallback"
    assert result.raw_amount == "60k"
    assert result.participant_hints == ["tao", "Bình"]


async def test_fallback_strips_leading_payer_from_description() -> None:
    adapter = AIExtractionAdapter(api_key="")

    pho = await adapter.extract("Nam trả 90k tiền phở")
    assert pho is not None
    assert pho.raw_amount == "90k"
    assert pho.payer_hint == "Nam"
    assert pho.description == "tiền phở"

    pho_split = await adapter.extract("Nam trả 90k tiền phở chia tao với Nam")
    assert pho_split is not None
    assert pho_split.description == "tiền phở"
    assert pho_split.participant_hints == ["tao", "Nam"]

    no_desc = await adapter.extract("Nam trả 90k")
    assert no_desc is not None
    assert no_desc.description == "Chi tiêu chung"


async def test_fallback_english_paid_and_non_payer_phrases() -> None:
    adapter = AIExtractionAdapter(api_key="")

    lan_paid = await adapter.extract("Lan paid 200k for dinner")
    assert lan_paid is not None
    assert lan_paid.raw_amount == "200k"
    assert lan_paid.payer_hint == "Lan"
    assert "dinner" in lan_paid.description.lower()

    bare_paid = await adapter.extract("Paid 300k for groceries")
    assert bare_paid is not None
    assert bare_paid.raw_amount == "300k"
    assert bare_paid.payer_hint == "sender"
    assert "groceries" in bare_paid.description.lower()
    assert "paid" not in bare_paid.description.lower()

    i_paid = await adapter.extract("I paid 150k for coffee")
    assert i_paid is not None
    assert i_paid.raw_amount == "150k"
    assert i_paid.payer_hint == "I"
    assert "coffee" in i_paid.description.lower()

    installment = await adapter.extract("Tiền trả góp 500k")
    assert installment is not None
    assert installment.raw_amount == "500k"
    assert installment.payer_hint == "sender"
    assert installment.description == "Tiền trả góp"


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_GEMINI") != "1",
    reason="Set RUN_LIVE_GEMINI=1 to run live Gemini API benchmark",
)
async def test_gemini_vs_fallback_benchmark() -> None:
    api_key = _load_gemini_key_from_env()
    if not api_key:
        # Also validate Settings class works cleanly in test mode when key is empty
        _ = Settings(
            app_env="test",
            telegram_bot_token="123456:TEST_TOKEN",
            telegram_webhook_secret="test-secret-0123456789abcdef",
            gemini_api_key="",
        )
        pytest.skip("GEMINI_API_KEY is not configured in .env")

    fallback_adapter = AIExtractionAdapter(api_key="")
    gemini_adapter = AIExtractionAdapter(api_key=api_key, timeout_s=15.0)

    print("\n=== Benchmark: Gemini API vs Rule-based Fallback ===")
    print(f"{'Input':<44} | {'Fallback (ms)':>13} | {'Gemini (ms)':>11} | {'Source':>8}")
    print("-" * 86)

    fb_times: list[float] = []
    gm_times: list[float] = []

    for text, _, _ in SAMPLE_MESSAGES:
        t0 = time.perf_counter()
        fb_res = await fallback_adapter.extract(text)
        fb_ms = (time.perf_counter() - t0) * 1000
        fb_times.append(fb_ms)

        t1 = time.perf_counter()
        gm_res = await gemini_adapter.extract(text)
        gm_ms = (time.perf_counter() - t1) * 1000
        gm_times.append(gm_ms)

        assert fb_res is not None
        assert gm_res is not None
        print(f"{text[:42]:<44} | {fb_ms:>13.3f} | {gm_ms:>11.2f} | {gm_res.source:>8}")

    avg_fb = sum(fb_times) / len(fb_times)
    avg_gm = sum(gm_times) / len(gm_times)
    speedup = avg_gm / max(avg_fb, 1e-6)
    print("-" * 86)
    print(
        f"Average: Fallback={avg_fb:.3f} ms vs Gemini={avg_gm:.2f} ms "
        f"(Fallback is {speedup:,.1f}x faster)"
    )


async def test_gemini_api_key_not_leaked_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    secret_key = "SECRET_GEMINI_KEY_123"
    captured_requests: list[httpx.Request] = []

    def _rate_limited_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        return httpx.Response(429, json={"error": "rate limit exceeded"})

    caplog.set_level(logging.WARNING)
    transport = httpx.MockTransport(_rate_limited_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = AIExtractionAdapter(api_key=secret_key, client=client)
        result = await adapter.extract("Mua nước uống 60k chia tao với Bình")

    assert len(captured_requests) == 1
    req = captured_requests[0]
    assert req.headers.get("x-goog-api-key") == secret_key
    assert secret_key not in str(req.url)
    assert result is not None
    assert result.source == "fallback"
    assert secret_key not in caplog.text
    assert "HTTPStatusError" in caplog.text


async def test_gemini_fallback_on_timeout_and_malformed_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING)

    def _timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    def _malformed_json_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "{not-valid-json"}]}}]},
        )

    def _missing_amount_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": '{"is_expense": true, "raw_amount": ""}'}]}}
                ]
            },
        )

    for handler in (_timeout_handler, _malformed_json_handler, _missing_amount_handler):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = AIExtractionAdapter(api_key="dummy-key", client=client)
            result = await adapter.extract("Mua nước uống 60k chia tao với Bình")
        assert result is not None
        assert result.source == "fallback"
        assert result.raw_amount == "60k"

    assert "ReadTimeout" in caplog.text
    assert "JSONDecodeError" in caplog.text
    assert "ValueError" in caplog.text


async def test_non_expense_or_missing_amount_returns_none() -> None:
    def _non_expense_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": '{"is_expense": false, "raw_amount": ""}'}]}}
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(_non_expense_handler)) as client:
        adapter = AIExtractionAdapter(api_key="dummy-key", client=client)
        assert await adapter.extract("Chào cả phòng") is None

    # UC03b-TC05: text without an amount returns None in fallback mode
    fallback = AIExtractionAdapter(api_key="")
    assert await fallback.extract("Mua đồ ăn sáng cho cả phòng") is None
