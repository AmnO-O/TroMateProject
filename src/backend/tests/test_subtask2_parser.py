"""Subtask 2 tests and benchmark feeding RawExtractionResult directly from Subtask 1."""

from __future__ import annotations

import time
import uuid

import pytest

from app.adapters.ai_extraction import AIExtractionAdapter
from app.adapters.vnd_parser import RawExtractionResult
from app.db.enums import SplitType
from app.services.errors import ValidationError
from app.services.expense_parser import (
    ExpenseParser,
    MemberContext,
    normalize_vnd_amount,
)

MEMBER_TAO = uuid.UUID("00000000-0000-0000-0000-000000000001")
MEMBER_NAM = uuid.UUID("00000000-0000-0000-0000-000000000002")
MEMBER_AN = uuid.UUID("00000000-0000-0000-0000-000000000003")

ROOM_MEMBERS = [
    MemberContext(member_id=MEMBER_TAO, display_name="Trần Minh", username="tranminh"),
    MemberContext(member_id=MEMBER_NAM, display_name="Nguyễn Văn Nam", username="namnguyen"),
    MemberContext(member_id=MEMBER_AN, display_name="Trần Bình An", username="binhan"),
]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("50k", 50_000),
        ("150k5", 150_500),
        ("650 nghìn", 650_000),
        ("1 củ rưỡi", 1_500_000),
        ("1tr2", 1_200_000),
        ("2 lít", 200_000),
        ("150.000đ", 150_000),
        (250_000, 250_000),
    ],
)
def test_normalize_vnd_slang_variants(raw: str | int, expected: int) -> None:
    assert normalize_vnd_amount(raw) == expected


def test_equal_split_with_remainder_from_raw_extraction() -> None:
    parser = ExpenseParser()
    extracted = RawExtractionResult(
        raw_amount="100k",
        description="Tiền nước tháng 10",
        payer_hint="sender",
        participant_hints=[],
        split_type="EQUAL",
        category_hint="Utilities",
    )

    parsed = parser.parse(
        extracted,
        sender_member_id=MEMBER_TAO,
        room_members=ROOM_MEMBERS,
    )

    assert parsed.total_amount == 100_000
    assert parsed.payer_member_id == MEMBER_TAO
    assert parsed.split_type == SplitType.EQUAL
    assert [s.share_amount for s in parsed.splits] == [33_334, 33_333, 33_333]
    assert sum(s.share_amount for s in parsed.splits) == 100_000


async def test_direct_feed_subtask1_to_subtask2() -> None:
    extractor = AIExtractionAdapter(api_key="")
    parser = ExpenseParser()

    raw_equal = await extractor.extract("Đi chợ mua thịt cá hết 150k chia tao với Nam")
    assert raw_equal is not None
    parsed_equal = parser.parse(
        raw_equal,
        sender_member_id=MEMBER_TAO,
        room_members=ROOM_MEMBERS,
    )
    assert parsed_equal.total_amount == 150_000
    assert [s.member_id for s in parsed_equal.splits] == [MEMBER_TAO, MEMBER_NAM]
    assert [s.share_amount for s in parsed_equal.splits] == [75_000, 75_000]

    raw_custom = await extractor.extract("Trà sữa 120k tao trả, Minh 70k, An 50k")
    assert raw_custom is not None
    parsed_custom = parser.parse(
        raw_custom,
        sender_member_id=MEMBER_TAO,
        room_members=ROOM_MEMBERS,
    )
    assert parsed_custom.split_type == SplitType.CUSTOM_AMOUNT
    assert [(s.member_id, s.share_amount) for s in parsed_custom.splits] == [
        (MEMBER_TAO, 70_000),
        (MEMBER_AN, 50_000),
    ]


def test_validation_errors() -> None:
    parser = ExpenseParser()

    with pytest.raises(ValidationError):
        normalize_vnd_amount("-50k")

    with pytest.raises(ValidationError):
        normalize_vnd_amount("0k")

    with pytest.raises(ValidationError):
        parser.parse(
            RawExtractionResult(
                raw_amount="120k",
                description="Trà sữa",
                split_type="CUSTOM_AMOUNT",
                custom_splits={"Minh": "70k", "An": "40k"},
            ),
            sender_member_id=MEMBER_TAO,
            room_members=ROOM_MEMBERS,
        )

    with pytest.raises(ValidationError):
        parser.parse(
            RawExtractionResult(
                raw_amount="100k",
                description="Ăn trưa",
                participant_hints=["Người Lạ"],
            ),
            sender_member_id=MEMBER_TAO,
            room_members=ROOM_MEMBERS,
        )


def test_parser_execution_time_benchmark() -> None:
    parser = ExpenseParser()
    samples = [
        RawExtractionResult(
            raw_amount="150k",
            description="Đi chợ mua thịt cá",
            payer_hint="tao",
            participant_hints=["tao", "Nam"],
            split_type="EQUAL",
            category_hint="Groceries",
        ),
        RawExtractionResult(
            raw_amount="1 củ rưỡi",
            description="Tiền wifi 6 tháng",
            payer_hint="sender",
            participant_hints=[],
            split_type="EQUAL",
            category_hint="Internet",
        ),
        RawExtractionResult(
            raw_amount="120k",
            description="Trà sữa",
            payer_hint="tao",
            split_type="CUSTOM_AMOUNT",
            custom_splits={"Minh": "70k", "An": "50k"},
            category_hint="Food & Drinks",
        ),
    ]

    t_single = time.perf_counter()
    for sample in samples:
        parser.parse(sample, sender_member_id=MEMBER_TAO, room_members=ROOM_MEMBERS)
    single_batch_ms = (time.perf_counter() - t_single) * 1000

    iterations = 1000
    t_batch = time.perf_counter()
    for i in range(iterations):
        parser.parse(
            samples[i % len(samples)],
            sender_member_id=MEMBER_TAO,
            room_members=ROOM_MEMBERS,
        )
    total_ms = (time.perf_counter() - t_batch) * 1000
    avg_us = (total_ms * 1000) / iterations

    print(
        f"\n[ExpenseParser Timing] 3-sample run={single_batch_ms:.4f} ms | "
        f"1000 runs={total_ms:.2f} ms (avg {avg_us:.2f} us/call)"
    )
    assert avg_us < 1000.0
