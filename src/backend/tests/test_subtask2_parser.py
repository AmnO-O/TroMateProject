# ruff: noqa: E402
"""Subtask 2 tests and execution-time benchmark using mock outputs from Subtask 1."""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

# Ensure imports resolve to this worktree even when pytest uses the root editable .venv
WORKTREE_BACKEND = Path(__file__).resolve().parents[1]
if str(WORKTREE_BACKEND) not in sys.path:
    sys.path.insert(0, str(WORKTREE_BACKEND))

import pytest

from app.db.enums import SplitType
from app.services.errors import ValidationError
from app.services.expense_parser import (
    ExpenseParser,
    ExtractionPayload,
    MemberContext,
    normalize_vnd_amount,
)

MEMBER_TAO = uuid.UUID("00000000-0000-0000-0000-000000000001")
MEMBER_NAM = uuid.UUID("00000000-0000-0000-0000-000000000002")
MEMBER_AN = uuid.UUID("00000000-0000-0000-0000-000000000003")

ROOM_MEMBERS = [
    MemberContext(member_id=MEMBER_TAO, display_name="Minh Kiệt", username="minhkiet"),
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


def test_equal_split_with_remainder_from_dict_payload() -> None:
    parser = ExpenseParser()
    # Mock dict shaped like Subtask 1 output (no import from app.adapters)
    subtask1_mock_output = {
        "raw_amount": "100k",
        "description": "Tiền nước tháng 10",
        "payer_hint": "sender",
        "participant_hints": [],
        "split_type": "EQUAL",
        "custom_splits": {},
        "category_hint": "Utilities",
    }

    parsed = parser.parse(
        subtask1_mock_output,
        sender_member_id=MEMBER_TAO,
        room_members=ROOM_MEMBERS,
    )

    assert parsed.total_amount == 100_000
    assert parsed.payer_member_id == MEMBER_TAO
    assert parsed.split_type == SplitType.EQUAL
    assert [s.share_amount for s in parsed.splits] == [33_334, 33_333, 33_333]
    assert sum(s.share_amount for s in parsed.splits) == 100_000


def test_subset_participants_and_custom_amount_split() -> None:
    parser = ExpenseParser()

    equal_subset = ExtractionPayload(
        raw_amount="150k",
        description="Đi chợ mua thịt cá",
        payer_hint="tao",
        participant_hints=["tao", "Nam"],
        split_type="EQUAL",
        category_hint="Groceries",
    )
    res_equal = parser.parse(
        equal_subset,
        sender_member_id=MEMBER_TAO,
        room_members=ROOM_MEMBERS,
    )
    assert res_equal.total_amount == 150_000
    assert [s.member_id for s in res_equal.splits] == [MEMBER_TAO, MEMBER_NAM]
    assert [s.share_amount for s in res_equal.splits] == [75_000, 75_000]

    custom_payload = ExtractionPayload(
        raw_amount="120k",
        description="Trà sữa",
        payer_hint="tao",
        participant_hints=["Minh Kiệt", "An"],
        split_type="CUSTOM_AMOUNT",
        custom_splits={"Minh Kiệt": "70k", "An": "50k"},
        category_hint="Food & Drinks",
    )
    res_custom = parser.parse(
        custom_payload,
        sender_member_id=MEMBER_TAO,
        room_members=ROOM_MEMBERS,
    )
    assert res_custom.split_type == SplitType.CUSTOM_AMOUNT
    assert [(s.member_id, s.share_amount) for s in res_custom.splits] == [
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
            {
                "raw_amount": "120k",
                "description": "Trà sữa",
                "split_type": "CUSTOM_AMOUNT",
                "custom_splits": {"Minh Kiệt": "70k", "An": "40k"},
            },
            sender_member_id=MEMBER_TAO,
            room_members=ROOM_MEMBERS,
        )

    with pytest.raises(ValidationError):
        parser.parse(
            {
                "raw_amount": "100k",
                "description": "Ăn trưa",
                "participant_hints": ["Người Lạ"],
            },
            sender_member_id=MEMBER_TAO,
            room_members=ROOM_MEMBERS,
        )


def test_parser_execution_time_benchmark() -> None:
    parser = ExpenseParser()
    payloads = [
        {
            "raw_amount": "150k",
            "description": "Đi chợ mua thịt cá",
            "payer_hint": "tao",
            "participant_hints": ["tao", "Nam"],
            "split_type": "EQUAL",
            "category_hint": "Groceries",
        },
        {
            "raw_amount": "1 củ rưỡi",
            "description": "Tiền wifi 6 tháng",
            "payer_hint": "sender",
            "participant_hints": [],
            "split_type": "EQUAL",
            "category_hint": "Internet",
        },
        {
            "raw_amount": "120k",
            "description": "Trà sữa",
            "payer_hint": "tao",
            "split_type": "CUSTOM_AMOUNT",
            "custom_splits": {"Minh Kiệt": "70k", "An": "50k"},
            "category_hint": "Food & Drinks",
        },
    ]

    t_single_start = time.perf_counter()
    for p in payloads:
        parser.parse(p, sender_member_id=MEMBER_TAO, room_members=ROOM_MEMBERS)
    single_batch_ms = (time.perf_counter() - t_single_start) * 1000

    iterations = 1000
    t_batch_start = time.perf_counter()
    for i in range(iterations):
        parser.parse(
            payloads[i % len(payloads)],
            sender_member_id=MEMBER_TAO,
            room_members=ROOM_MEMBERS,
        )
    total_ms = (time.perf_counter() - t_batch_start) * 1000
    avg_us = (total_ms * 1000) / iterations

    print(
        f"\n[ExpenseParser Timing] 3-payload sample={single_batch_ms:.4f} ms | "
        f"1000 runs={total_ms:.2f} ms (avg {avg_us:.2f} us/call)"
    )
    assert avg_us < 1000.0
