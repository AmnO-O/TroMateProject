"""Domain service for VND normalization and roommate expense split calculation."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.adapters.vnd_parser import RawExtractionResult
from app.db.enums import SplitType
from app.services.errors import ValidationError

_SLANG_RE = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn|tr|triệu|củ|lít|đ|vnd|đồng)?"
    r"(?:\s*(rưỡi)|(\d+))?\s*$",
    re.IGNORECASE,
)
_THOUSANDS_RE = re.compile(r"^\d{1,3}(?:[.,]\d{3})+$")
_SELF_PRONOUNS = frozenset({"", "sender", "tao", "tôi", "mình", "tớ"})

_UNIT_MULTIPLIERS: dict[str, int] = {
    "k": 1_000,
    "nghìn": 1_000,
    "ngàn": 1_000,
    "lít": 100_000,
    "tr": 1_000_000,
    "triệu": 1_000_000,
    "củ": 1_000_000,
    "đ": 1,
    "vnd": 1,
    "đồng": 1,
}


@dataclass(frozen=True, slots=True)
class MemberContext:
    """Minimal room member projection needed to resolve names to member IDs."""

    member_id: uuid.UUID
    display_name: str
    username: str | None = None


@dataclass(frozen=True, slots=True)
class ComputedSplit:
    """Single participant share ready to persist as ``ExpenseSplit``."""

    member_id: uuid.UUID
    share_amount: int


@dataclass(frozen=True, slots=True)
class ParsedExpense:
    """Normalized expense domain result ready for persistence."""

    description: str
    total_amount: int
    payer_member_id: uuid.UUID
    split_type: SplitType
    splits: list[ComputedSplit]
    category_name: str


def normalize_vnd_amount(raw: str | int) -> int:
    """Convert Vietnamese currency slang or formatted text into whole VND (> 0)."""

    if isinstance(raw, bool):
        raise ValidationError("Giá trị số tiền không hợp lệ.")
    if isinstance(raw, int):
        if raw <= 0:
            raise ValidationError("Số tiền chi tiêu phải lớn hơn 0đ.")
        return raw

    text = str(raw).strip()
    if not text:
        raise ValidationError("Số tiền chi tiêu không được để trống.")
    if text.startswith("-"):
        raise ValidationError("Số tiền chi tiêu phải lớn hơn 0đ.")

    plain_candidate = re.sub(r"(?i)\s*(?:đ|vnd|đồng)\s*$", "", text).strip()
    if _THOUSANDS_RE.fullmatch(plain_candidate):
        value = int(plain_candidate.replace(".", "").replace(",", ""))
        if value <= 0:
            raise ValidationError("Số tiền chi tiêu phải lớn hơn 0đ.")
        return value

    match = _SLANG_RE.fullmatch(text)
    if not match:
        raise ValidationError(f'Không nhận diện được số tiền hợp lệ: "{raw}".')

    num_str, unit_raw, ruoi_raw, digits_raw = match.groups()
    suffix_raw = ruoi_raw or digits_raw
    unit = (unit_raw or "").lower()
    multiplier = _UNIT_MULTIPLIERS.get(unit, 1)

    if unit in {"", "đ", "vnd", "đồng"} and ("." in num_str or "," in num_str):
        raise ValidationError(
            f'Số tiền "{raw}" có dấu thập phân nhưng thiếu đơn vị (ví dụ: k, tr, đ).'
        )

    base_num = float(num_str.replace(",", "."))
    total = round(base_num * multiplier)

    if suffix_raw:
        suffix = suffix_raw.lower()
        if multiplier <= 1:
            raise ValidationError(f'Số tiền "{raw}" chứa phần đuôi không hợp lệ.')
        if suffix == "rưỡi":
            total += multiplier // 2
        elif suffix.isdigit():
            # e.g. "1tr2" -> +200_000, "150k5" -> +500
            scale = multiplier // (10 ** len(suffix))
            if scale <= 0:
                raise ValidationError(f'Phần lẻ trong số tiền "{raw}" không hợp lệ.')
            total += int(suffix) * scale

    if total <= 0:
        raise ValidationError("Số tiền chi tiêu phải lớn hơn 0đ.")
    return total


class ExpenseParser:
    """Normalizes ``RawExtractionResult`` directly and computes validated VND splits."""

    def parse(
        self,
        extracted: RawExtractionResult,
        *,
        sender_member_id: uuid.UUID,
        room_members: Sequence[MemberContext],
    ) -> ParsedExpense:
        if not room_members:
            raise ValidationError("Phòng trọ phải có ít nhất một thành viên.")

        total_amount = normalize_vnd_amount(extracted.raw_amount)
        member_index = self._build_member_index(room_members)

        payer_member_id = self._resolve_member(
            extracted.payer_hint,
            sender_member_id=sender_member_id,
            member_index=member_index,
        )

        split_type_upper = extracted.split_type.strip().upper()
        if split_type_upper == SplitType.CUSTOM_AMOUNT:
            splits = self._compute_custom_splits(
                total_amount=total_amount,
                custom_splits=extracted.custom_splits,
                sender_member_id=sender_member_id,
                member_index=member_index,
            )
            resolved_split_type = SplitType.CUSTOM_AMOUNT
        elif split_type_upper == SplitType.EQUAL:
            target_ids = self._resolve_participants(
                extracted.participant_hints,
                sender_member_id=sender_member_id,
                room_members=room_members,
                member_index=member_index,
            )
            display_names = {m.member_id: m.display_name for m in room_members}
            splits = self._compute_equal_splits(
                total_amount,
                target_ids,
                payer_member_id=payer_member_id,
                display_names=display_names,
            )
            resolved_split_type = SplitType.EQUAL
        else:
            raise ValidationError(f'Kiểu chia tiền "{extracted.split_type}" không được hỗ trợ.')

        description = extracted.description.strip() or "Chi tiêu chung"
        category_name = extracted.category_hint.strip() or "Other"

        return ParsedExpense(
            description=description,
            total_amount=total_amount,
            payer_member_id=payer_member_id,
            split_type=resolved_split_type,
            splits=splits,
            category_name=category_name,
        )

    @staticmethod
    def _build_member_index(room_members: Sequence[MemberContext]) -> dict[str, uuid.UUID]:
        index: dict[str, uuid.UUID] = {}
        first_name_counts: dict[str, int] = {}

        for member in room_members:
            display = member.display_name.strip().lower()
            if display:
                index[display] = member.member_id
                last_token = display.split()[-1]
                first_name_counts[last_token] = first_name_counts.get(last_token, 0) + 1
            if member.username:
                uname = member.username.strip().lstrip("@").lower()
                if uname:
                    index[uname] = member.member_id

        # Allow matching by unique short given name (e.g. "Nam" for "Nguyễn Văn Nam")
        for member in room_members:
            display = member.display_name.strip().lower()
            if display:
                last_token = display.split()[-1]
                if first_name_counts.get(last_token) == 1 and last_token not in index:
                    index[last_token] = member.member_id

        return index

    @staticmethod
    def _resolve_member(
        hint: str,
        *,
        sender_member_id: uuid.UUID,
        member_index: dict[str, uuid.UUID],
    ) -> uuid.UUID:
        key = hint.strip().lstrip("@").lower()
        if key in member_index:
            return member_index[key]
        if key in _SELF_PRONOUNS:
            return sender_member_id
        raise ValidationError(
            f'Không tìm thấy thành viên "{hint}" trong phòng. '
            f"{hint} cần nhắn /start hoặc /new trong nhóm trước."
        )

    def _resolve_participants(
        self,
        hints: Sequence[str],
        *,
        sender_member_id: uuid.UUID,
        room_members: Sequence[MemberContext],
        member_index: dict[str, uuid.UUID],
    ) -> list[uuid.UUID]:
        if not hints:
            return [m.member_id for m in room_members]

        seen: set[uuid.UUID] = set()
        resolved: list[uuid.UUID] = []
        for hint in hints:
            member_id = self._resolve_member(
                hint,
                sender_member_id=sender_member_id,
                member_index=member_index,
            )
            if member_id not in seen:
                seen.add(member_id)
                resolved.append(member_id)
        return resolved

    @staticmethod
    def _compute_equal_splits(
        total_amount: int,
        participant_ids: Sequence[uuid.UUID],
        *,
        payer_member_id: uuid.UUID,
        display_names: Mapping[uuid.UUID, str],
    ) -> list[ComputedSplit]:
        """Split equally; assign modulo remainder to payer or first A-Z member (§2.5.3)."""

        count = len(participant_ids)
        if count == 0:
            raise ValidationError("Cần ít nhất một người tham gia chia tiền.")
        base, remainder = divmod(total_amount, count)
        if base == 0:
            raise ValidationError("Phần chia của mỗi người phải ít nhất 1đ.")

        absorber_id: uuid.UUID | None = None
        if remainder > 0:
            if payer_member_id in participant_ids:
                absorber_id = payer_member_id
            else:
                absorber_id = min(
                    participant_ids,
                    key=lambda mid: (display_names.get(mid, "").strip().casefold(), str(mid)),
                )

        return [
            ComputedSplit(
                member_id=member_id,
                share_amount=base + (remainder if member_id == absorber_id else 0),
            )
            for member_id in participant_ids
        ]

    def _compute_custom_splits(
        self,
        *,
        total_amount: int,
        custom_splits: Mapping[str, str | int],
        sender_member_id: uuid.UUID,
        member_index: dict[str, uuid.UUID],
    ) -> list[ComputedSplit]:
        if not custom_splits:
            raise ValidationError("Danh sách chia tiền cụ thể không được để trống.")

        merged: dict[uuid.UUID, int] = {}
        for hint, raw_share in custom_splits.items():
            member_id = self._resolve_member(
                hint,
                sender_member_id=sender_member_id,
                member_index=member_index,
            )
            share_amount = normalize_vnd_amount(raw_share)
            merged[member_id] = merged.get(member_id, 0) + share_amount

        total_splits = sum(merged.values())
        if total_splits != total_amount:
            raise ValidationError(
                f"Tổng các phần chia ({total_splits:,}đ) không khớp tổng tiền ({total_amount:,}đ)."
            )

        return [
            ComputedSplit(member_id=member_id, share_amount=amount)
            for member_id, amount in merged.items()
        ]
