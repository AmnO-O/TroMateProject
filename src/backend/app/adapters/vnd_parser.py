"""Rule-based Vietnamese expense text parser (fallback for AIExtractionAdapter)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_UNIT_AMOUNT_BODY = (
    r"\d+(?:[.,]\d+)?\s*(?:k|nghìn|ngàn|tr|triệu|củ|lít|đ|vnd|đồng)(?:\s*rưỡi|\d+)?"
    r"|\d{1,3}(?:[.,]\d{3})+\s*(?:đ|vnd|đồng)?"
)
_AMOUNT_BODY = rf"{_UNIT_AMOUNT_BODY}|\d{{4,9}}"
UNIT_AMOUNT_RE = re.compile(rf"(?i)(?<![\w#-])({_UNIT_AMOUNT_BODY})(?!\w)")
AMOUNT_RE = re.compile(rf"(?i)(?<![\w#-])({_AMOUNT_BODY})(?!\w)")
PAYER_RE = re.compile(r"(?i)\b([A-Za-zÀ-ỹ0-9_]+)\s+(?:trả|chi|ứng|thanh\s+toán|paid)\b")
SPLIT_CLAUSE_RE = re.compile(r"(?i)\b(?:chia|tính\s+tiền|share)\b(.*)$")
_TAIL_CHO_RE = re.compile(r"(?i)^\s*cho\b(.*)$")
CUSTOM_PAIR_RE = re.compile(rf"(?i)\b([A-Za-zÀ-ỹ][A-Za-zÀ-ỹ0-9_]*)\s+({_AMOUNT_BODY})(?!\w)")

_ROOM_WIDE_MARKERS = ("cả phòng", "cả nhà", "tất cả", "mọi người", "all")
_STOPWORDS = {"cho", "đều", "nha", "nhé", "nhe", "ạ", "đi", "luôn", "này", "giúp"}
_IGNORED_PAIR_PREFIXES = {"hết", "tổng", "giá", "tiền", "khoảng", "tầm", "hôm", "tháng", "ngày"}
_NON_PAYER_WORDS = frozenset(
    {
        "ai",
        "người",
        "tự",
        "đã",
        "vừa",
        "tiền",
        "khoản",
        "phí",
        "mua",
        "đi",
        "cho",
        "để",
        "sẽ",
        "chưa",
        "không",
        "phải",
        "cần",
        "mới",
        "for",
        "to",
    }
)

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Rent",
        (
            "tiền phòng",
            "tiền thuê",
            "tiền nhà",
            "tiền trọ",
            "thuê nhà",
            "thuê phòng",
            "phòng trọ",
        ),
    ),
    (
        "Utilities",
        (
            "tiền điện",
            "tiền nước",
            "hóa đơn nước",
            "hóa đơn điện",
            "điện",
            "rác",
            "ga",
            "gas",
            "vệ sinh",
        ),
    ),
    ("Internet", ("wifi", "mạng", "internet", "4g", "cáp quang")),
    ("Groceries", ("chợ", "siêu thị", "thịt", "cá", "rau", "trứng", "gạo", "bách hóa")),
    (
        "Food & Drinks",
        (
            "ăn",
            "cơm",
            "phở",
            "bún",
            "mì",
            "trà sữa",
            "cafe",
            "cà phê",
            "nhậu",
            "bia",
            "nước ngọt",
            "nước uống",
            "nước suối",
        ),
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
    tentative_participants: bool = False


def _infer_category(text: str) -> str:
    lowered = text.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", lowered) for keyword in keywords):
            return category
    return "Other"


def _extract_payer(text: str) -> str:
    match = PAYER_RE.search(text)
    if not match:
        return "sender"
    candidate = match.group(1).strip()
    if candidate.lower() in _NON_PAYER_WORDS:
        return "sender"
    return candidate


def _extract_participants(text: str, tail: str = "") -> tuple[list[str], bool]:
    match = SPLIT_CLAUSE_RE.search(text)
    tentative = False
    if not match:
        match = _TAIL_CHO_RE.search(tail)
        tentative = True
    if not match:
        return [], False
    clause = match.group(1).strip()
    lowered = clause.lower()
    if any(marker in lowered for marker in _ROOM_WIDE_MARKERS):
        return [], False

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
    return participants, tentative


_LEADING_NOISE_RE = re.compile(r"(?i)^paid\b\s*")
_TRAILING_CONNECTOR_RE = re.compile(r"(?i)\b(?:hết|tổng(?:\s+cộng)?|giá|tốn|mất|là)\s*$")


def _strip_description_noise(text: str) -> str:
    def _replace_payer(match: re.Match[str]) -> str:
        return match.group(0) if match.group(1).lower() in _NON_PAYER_WORDS else ""

    cleaned = PAYER_RE.sub(_replace_payer, text)
    cleaned = " ".join(cleaned.split()).strip(" :,-.")
    cleaned = _LEADING_NOISE_RE.sub("", cleaned)
    cleaned = _TRAILING_CONNECTOR_RE.sub("", cleaned)
    return " ".join(cleaned.split()).strip(" :,-.")


def _clean_description(prefix: str, tail: str = "") -> str:
    cleaned_prefix = _strip_description_noise(prefix)
    if cleaned_prefix:
        return cleaned_prefix

    tail_without_split = _TAIL_CHO_RE.sub("", SPLIT_CLAUSE_RE.sub("", tail))
    cleaned_tail = _strip_description_noise(tail_without_split)
    return cleaned_tail or "Chi tiêu chung"


def extract_expense_fallback(text: str) -> RawExtractionResult | None:
    """Extract raw expense fields from Vietnamese natural text without network/LLM."""

    normalized = " ".join(text.strip().split())
    if not normalized:
        return None

    first_amount = UNIT_AMOUNT_RE.search(normalized) or AMOUNT_RE.search(normalized)
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
        tentative_participants = False
    else:
        custom_splits = {}
        split_type = "EQUAL"
        participant_hints, tentative_participants = _extract_participants(normalized, tail)

    return RawExtractionResult(
        raw_amount=raw_amount,
        description=_clean_description(prefix, tail),
        payer_hint=_extract_payer(normalized),
        participant_hints=participant_hints,
        split_type=split_type,
        custom_splits=custom_splits,
        category_hint=_infer_category(normalized),
        source="fallback",
        tentative_participants=tentative_participants,
    )
