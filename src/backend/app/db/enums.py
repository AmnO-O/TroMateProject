"""Enumerations stored as VARCHAR + CHECK columns.

Values follow the SCRUM-117 data dictionary, corrected where the Use-case
Specification v2.0 (SCRUM-114) is more specific; see ``docs`` notes in the README.
"""

from __future__ import annotations

from enum import StrEnum


class PlanType(StrEnum):
    FREE = "FREE"
    PRO = "PRO"


class ReviewDefaultAction(StrEnum):
    """Action applied lazily to a PENDING expense whose review deadline has passed."""

    CONFIRM = "CONFIRM"  # -> CONFIRMED (UC06 auto-confirm)
    DECLINE = "DECLINE"  # -> CANCELLED with ``auto_resolved = true``


class MemberRole(StrEnum):
    MEMBER = "MEMBER"
    ROOM_REP = "ROOM_REP"


class SplitType(StrEnum):
    EQUAL = "EQUAL"
    CUSTOM_AMOUNT = "CUSTOM_AMOUNT"
    CUSTOM_RATIO = "CUSTOM_RATIO"


class ExpenseStatus(StrEnum):
    """Expense state machine (BR01, BR04).

    PENDING -> CONFIRMED  every involved member agreed, or the deadline passed (CONFIRM)
    PENDING -> DISPUTED   a member rejected; only the creator may edit or cancel
    PENDING/DISPUTED -> PENDING  edited: new version, approvals cleared except the editor's
    PENDING/DISPUTED -> CANCELLED  creator cancelled, or the deadline passed (DECLINE)

    CONFIRMED and CANCELLED are closed. Only CONFIRMED expenses reach the ledger.
    """

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    DISPUTED = "DISPUTED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class SourceType(StrEnum):
    TEXT = "TEXT"
    PHOTO = "PHOTO"
    METER = "METER"


class ApprovalDecision(StrEnum):
    AGREE = "AGREE"
    REJECT = "REJECT"


class RejectionReason(StrEnum):
    """Reasons offered in UC05-AF02."""

    WRONG_AMOUNT = "WRONG_AMOUNT"
    WRONG_PARTICIPANTS = "WRONG_PARTICIPANTS"
    NOT_MY_EXPENSE = "NOT_MY_EXPENSE"
    DUPLICATE = "DUPLICATE"
    OTHER = "OTHER"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    RECEIVED = "RECEIVED"


class LedgerEntryType(StrEnum):
    EXPENSE = "EXPENSE"
    SETTLEMENT = "SETTLEMENT"


# BR03 (v3.0): auto-confirmation window adopted via UC13 is 1 to 30 days (in minutes).
MIN_REVIEW_WINDOW_MINUTES: int = 24 * 60
MAX_REVIEW_WINDOW_MINUTES: int = 30 * 24 * 60

# BR06: system categories seeded for every room; they cannot be renamed or archived.
DEFAULT_CATEGORIES: tuple[str, ...] = (
    "Food & Drinks",
    "Groceries",
    "Household Supplies",
    "Utilities",
    "Rent",
    "Internet",
    "Other",
)
