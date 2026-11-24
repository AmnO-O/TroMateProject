"""Rule-based Vietnamese expense text parser (fallback for AIExtractionAdapter)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_AMOUNT_BODY = (
    r"\d+(?:[.,]\d+)?\s*(?:k|nghìn|ngàn|tr|triệu|củ|lít|đ|vnd)(?:\s*(?:rưỡi|\d+))?"
    r"|\d{1,3}(?:[.,]\d{3})+\s*(?:đ|vnd)?"
    r"|\d{4,9}"
)
AMOUNT_RE = re.compile(rf"(?i)(?<!\w)({_AMOUNT_BODY})(?!\w)")
PAYER_RE = re.compile(r"(?i)\b([A-Za-zÀ-ỹ0-9_]+)\s+(?:trả|chi|ứng|thanh\s+toán)\b")
SPLIT_CLAUSE_RE = re.compile(r"(?i)\b(?:chia|tính\s+tiền|share)\b(.*)$")
CUSTOM_PAIR_RE = re.compile(
    rf"(?i)\b([A-Za-zÀ-ỹ][A-Za-zÀ-ỹ0-9_]*)\s+({_AMOUNT_BODY})(?!\w)"
)

_ROOM_WIDE_MARKERS = ("cả phòng", "tất cả", "mọi người", "all")
_STOPWORDS = {"cho", "đều", "nha", "nhé", "nhe", "ạ", "đi", "luôn", "này", "giúp"}
_IGNORED_PAIR_PREFIXES = {"hết", "tổng", "giá", "tiền", "khoảng", "tầm", "hôm", "tháng", "ngày"}

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Utilities", ("điện", "nước", "rác", "ga", "gas", "vệ sinh")),
    ("Internet", ("wifi", "mạng", "internet", "4g", "cáp quang")),
    ("Rent", ("tiền nhà", "tiền trọ", "thuê nhà", "thuê phòng", "phòng trọ")),
    ("Groceries", ("chợ", "siêu thị", "thịt", "cá", "rau", "trứng", "gạo", "bách hóa")),
    (
        "Food & Drinks",
        ("ăn", "cơm", "phở", "bún", "mì", "trà sữa", "cafe", "cà phê", "nhậu", "bia", "nước ngọt"),
    ),
    ("Household Supplies", ("xà phòng", "nước rửa", "giấy", "bột giặt", "chổi", "đồ dùng")),
)


@dataclass(slots=True)
class RawExtractionResult:
    """Raw structured extraction produced by Gemini or the rule-based fallback."""

    raw_amount: str
    description: str
    payer_hint: str = "sender"
    participant_hints: list[str] = field(default_factory=list)
    split_type: str = "EQUAL"
    custom_splits: dict[str, str] = field(default_factory=dict)
    category_hint: str = "Other"
    source: str = "fallback"


def _infer_category(text: str) -> str:
    lowered = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return category
    return "Other"


def _extract_payer(text: str) -> str:
    match = PAYER_RE.search(text)
    if not match:
        return "sender"
    candidate = match.group(1).strip()
    if candidate.lower() in {"ai", "người", "tự", "đã", "vừa"}:
        return "sender"
    return candidate


def _extract_participants(text: str) -> list[str]:
    match = SPLIT_CLAUSE_RE.search(text)
    if not match:
        return []
    clause = match.group(1).strip()
    lowered = clause.lower()
    if any(marker in lowered for marker in _ROOM_WIDE_MARKERS):
        return []

    # Strip trailing payer mentions such as "tao trả" from the split clause
    clause = re.sub(r"(?i),?\s*[A-Za-zÀ-ỹ0-9_]+\s+(?:trả|chi|ứng).*$", "", clause)
    tokens = re.split(r"(?i)\s*(?:,|;|\bvà\b|\bvới\b|&)\s*", clause)
    participants: list[str] = []
    for token in tokens:
        words = [w for w in token.strip(" .!?").split() if w.lower() not in _STOPWORDS]
        if not words:
            continue
        name = " ".join(words)
        if name.lower() not in {p.lower() for p in participants}:
            participants.append(name)
    return participants


def _clean_description(prefix: str) -> str:
    cleaned = prefix.strip(" :,-.")
    cleaned = re.sub(r"(?i)\b(?:hết|tổng(?:\s+cộng)?|giá|tốn|mất|là)\s*$", "", cleaned)
    cleaned = cleaned.strip(" :,-.")
    return cleaned or "Chi tiêu chung"


def extract_expense_fallback(text: str) -> RawExtractionResult | None:
    """Extract raw expense fields from Vietnamese natural text without network/LLM."""

    normalized = " ".join(text.strip().split())
    if not normalized:
        return None

    first_amount = AMOUNT_RE.search(normalized)
    if not first_amount:
        return None

    raw_amount = " ".join(first_amount.group(1).split())
    prefix = normalized[: first_amount.start()]
    tail = normalized[first_amount.end() :]

    custom_splits: dict[str, str] = {}
    for pair in CUSTOM_PAIR_RE.finditer(tail):
        name = pair.group(1).strip()
        if name.lower() in _IGNORED_PAIR_PREFIXES:
            continue
        custom_splits[name] = " ".join(pair.group(2).split())

    if len(custom_splits) >= 2:
        split_type = "CUSTOM_AMOUNT"
        participant_hints = list(custom_splits.keys())
    else:
        custom_splits = {}
        split_type = "EQUAL"
        participant_hints = _extract_participants(normalized)

    return RawExtractionResult(
        raw_amount=raw_amount,
        description=_clean_description(prefix),
        payer_hint=_extract_payer(normalized),
        participant_hints=participant_hints,
        split_type=split_type,
        custom_splits=custom_splits,
        category_hint=_infer_category(normalized),
        source="fallback",
    )
